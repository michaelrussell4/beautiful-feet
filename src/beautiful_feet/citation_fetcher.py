"""Fetcher and parser for 19th-century BYU Scripture Citation Index entries."""

from __future__ import annotations
import os
import re
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from .models import Citation

logger = logging.getLogger(__name__)

BASE_URL = "https://scriptures.byu.edu/citation_index/citation_ajax"

# Journal of Discourses Volume Publication Years
JD_VOLUME_YEARS: Dict[int, int] = {
    1: 1854,
    2: 1855,
    3: 1856,
    4: 1857,
    5: 1858,
    6: 1859,
    7: 1860,
    8: 1861,
    9: 1862,
    10: 1865,
    11: 1867,
    12: 1869,
    13: 1871,
    14: 1872,
    15: 1873,
    16: 1874,
    17: 1875,
    18: 1877,
    19: 1878,
    20: 1880,
    21: 1881,
    22: 1882,
    23: 1883,
    24: 1884,
    25: 1885,
    26: 1886,
}

# Book metadata: book_id -> (slug, name, num_chapters)
BOM_BOOKS = [
    (205, "1-ne", "1 Nephi", 22),
    (206, "2-ne", "2 Nephi", 33),
    (207, "jacob", "Jacob", 7),
    (208, "enos", "Enos", 1),
    (209, "jarom", "Jarom", 1),
    (210, "omni", "Omni", 1),
    (211, "w-of-m", "Words of Mormon", 1),
    (212, "mosiah", "Mosiah", 29),
    (213, "alma", "Alma", 63),
    (214, "hel", "Helaman", 16),
    (215, "3-ne", "3 Nephi", 30),
    (216, "4-ne", "4 Nephi", 1),
    (217, "morm", "Mormon", 9),
    (218, "ether", "Ether", 15),
    (219, "moroni", "Moroni", 10),
]


def parse_citation_item(ref_text: str, talk_title: str = "") -> Optional[Citation]:
    """Parse reference text into Citation if it belongs to scoped 19th-century sources.

    Allowed sources:
    - Journal of Discourses (JD)
    - Teachings of the Prophet Joseph Smith (TPJS)
    - History of the Church (HC)
    - Times and Seasons (TS)
    - Millennial Star (MS)
    """
    ref_text = ref_text.strip()
    if not ref_text:
        return None

    # 1. Journal of Discourses: JD 23:48b, John Taylor
    m_jd = re.match(r"^JD\s+(\d+):([\d\w]+)(?:,\s*(.+))?$", ref_text, re.IGNORECASE)
    if m_jd:
        vol = int(m_jd.group(1))
        page = m_jd.group(2)
        speaker = (m_jd.group(3) or "").strip()
        year = JD_VOLUME_YEARS.get(vol)
        cit_str = f"JD {vol}:{page}"
        return Citation(
            speaker=speaker,
            source="Journal of Discourses",
            citation=cit_str,
            year=year,
            talk_title=talk_title,
        )

    # 2. Teachings of the Prophet Joseph Smith: TPJS 232, Joseph Smith
    m_tpjs = re.match(r"^TPJS\s+([\d\w]+)(?:,\s*(.+))?$", ref_text, re.IGNORECASE)
    if m_tpjs:
        page = m_tpjs.group(1)
        speaker = (m_tpjs.group(2) or "Joseph Smith").strip()
        cit_str = f"TPJS {page}"
        return Citation(
            speaker=speaker,
            source="Teachings of the Prophet Joseph Smith",
            citation=cit_str,
            year=None,
            talk_title=talk_title,
        )

    # 3. History of the Church: HC 4:567, Joseph Smith
    m_hc = re.match(r"^HC\s+(\d+):([\d\w]+)(?:,\s*(.+))?$", ref_text, re.IGNORECASE)
    if m_hc:
        vol = int(m_hc.group(1))
        page = m_hc.group(2)
        speaker = (m_hc.group(3) or "Joseph Smith").strip()
        cit_str = f"HC {vol}:{page}"
        return Citation(
            speaker=speaker,
            source="History of the Church",
            citation=cit_str,
            year=None,
            talk_title=talk_title,
        )

    # 4. Times and Seasons: TS 3:800
    m_ts = re.match(r"^TS\s+(\d+):([\d\w]+)(?:,\s*(.+))?$", ref_text, re.IGNORECASE)
    if m_ts:
        vol = int(m_ts.group(1))
        page = m_ts.group(2)
        speaker = (m_ts.group(3) or "").strip()
        cit_str = f"TS {vol}:{page}"
        return Citation(
            speaker=speaker,
            source="Times and Seasons",
            citation=cit_str,
            year=None,
            talk_title=talk_title,
        )

    # 5. Millennial Star: MS 12:34
    m_ms = re.match(r"^MS\s+(\d+):([\d\w]+)(?:,\s*(.+))?$", ref_text, re.IGNORECASE)
    if m_ms:
        vol = int(m_ms.group(1))
        page = m_ms.group(2)
        speaker = (m_ms.group(3) or "").strip()
        cit_str = f"MS {vol}:{page}"
        return Citation(
            speaker=speaker,
            source="Millennial Star",
            citation=cit_str,
            year=None,
            talk_title=talk_title,
        )

    return None


def format_verse_numbers(v_nums: List[int]) -> str:
    """Format a list of sorted verse integers into standard ranges like '18–20' or '1–2, 19–20'."""
    if not v_nums:
        return ""
    v_nums = sorted(set(v_nums))
    ranges = []
    start = v_nums[0]
    prev = v_nums[0]
    for n in v_nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            if start == prev:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}–{prev}")
            start = n
            prev = n
    if start == prev:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}–{prev}")
    return ", ".join(ranges)


def deduplicate_citations_to_last_verse(
    citation_dict: Dict[str, List[Citation]]
) -> Dict[str, List[Citation]]:
    """Deduplicate multi-verse citations so each unique citation appears ONLY on the last verse of its range.

    If a discourse citation references e.g. 1 Ne. 1:18-20, BYU Citation Index indexes
    that identical excerpt under verses 18, 19, and 20.
    This function consolidates the citation so it only attaches to verse 20 (the last verse in the range),
    recording the covered range on the Citation object (e.g. '18–20').
    """
    from collections import defaultdict

    chap_cits: Dict[str, Dict[Tuple, List[Tuple[int, str, Citation]]]] = defaultdict(lambda: defaultdict(list))

    for v_key, c_list in citation_dict.items():
        parts = v_key.rsplit("-", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        ch_key = parts[0]
        v_num = int(parts[1])
        for c in c_list:
            sig = (
                (c.source, c.talk_id, c.target_id)
                if (c.talk_id and c.target_id)
                else (c.source, c.citation, c.speaker, c.talk_title)
            )
            chap_cits[ch_key][sig].append((v_num, v_key, c))

    deduped: Dict[str, List[Citation]] = defaultdict(list)

    for ch_key, sig_map in chap_cits.items():
        for sig, vlist in sig_map.items():
            vlist.sort(key=lambda x: x[0])
            last_vnum, last_vkey, cit = vlist[-1]
            v_nums = [x[0] for x in vlist]

            if len(v_nums) > 1:
                cit.covered_range = format_verse_numbers(v_nums)
            elif not cit.covered_range:
                cit.covered_range = str(last_vnum)


            deduped[last_vkey].append(cit)

    # Sort each verse's citations and preserve chapter canonical order
    sorted_result: Dict[str, List[Citation]] = {}
    for vk in sorted(
        deduped.keys(),
        key=lambda k: (k.rsplit("-", 1)[0], int(k.rsplit("-", 1)[1])),
    ):
        sorted_result[vk] = deduped[vk]

    return sorted_result


def fetch_verse_citations(
    b_id: int, b_slug: str, ch: int, v_str: str, session: requests.Session
) -> Tuple[str, List[Citation]]:
    """Fetch citations for a specific verse from both 1830-1930 sources and TPJS."""
    verse_key = f"{b_slug}-{ch}-{v_str}"
    citations: List[Citation] = []
    seen = set()

    # Query 1: All 1830-1930 sources
    u1 = f"{BASE_URL}/Any/1830/1930/all/s/i/{b_id}/{ch}?verses={v_str}"
    try:
        r1 = session.get(u1, timeout=12)
        soup1 = BeautifulSoup(r1.text, "html.parser")
        for li in soup1.find_all("li"):
            ref = li.find(class_="reference")
            talk = li.find(class_="talktitle")
            if ref:
                ref_txt = ref.get_text(" ", strip=True)
                talk_txt = talk.get_text(" ", strip=True) if talk else ""
                cit = parse_citation_item(ref_txt, talk_txt)
                if cit:
                    sig = (cit.source, cit.citation, cit.speaker)
                    if sig not in seen:
                        seen.add(sig)
                        citations.append(cit)
    except Exception as e:
        logger.debug(f"Error fetching 1830-1930 citations for {verse_key}: {e}")

    # Query 2: TPJS
    u2 = f"{BASE_URL}/Any/1830/2026/T/s/i/{b_id}/{ch}?verses={v_str}"
    try:
        r2 = session.get(u2, timeout=12)
        soup2 = BeautifulSoup(r2.text, "html.parser")
        for li in soup2.find_all("li"):
            ref = li.find(class_="reference")
            talk = li.find(class_="talktitle")
            if ref:
                ref_txt = ref.get_text(" ", strip=True)
                talk_txt = talk.get_text(" ", strip=True) if talk else ""
                cit = parse_citation_item(ref_txt, talk_txt)
                if cit:
                    sig = (cit.source, cit.citation, cit.speaker)
                    if sig not in seen:
                        seen.add(sig)
                        citations.append(cit)
    except Exception as e:
        logger.debug(f"Error fetching TPJS citations for {verse_key}: {e}")

    return verse_key, citations


def fetch_all_citations(
    cache_path: str = "data/early_citations.json", force_refresh: bool = False
) -> Dict[str, List[Citation]]:
    """Fetch all early Book of Mormon citations from BYU SCI or load from cache."""
    if os.path.exists(cache_path) and not force_refresh:
        logger.info(f"Loading early citations from cache: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_dict = {
            v_key: [Citation.from_dict(c) for c in cit_list]
            for v_key, cit_list in data.items()
        }
        return deduplicate_citations_to_last_verse(raw_dict)

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    logger.info("Scanning all 239 Book of Mormon chapters for verses with early citations...")

    session = requests.Session()

    # Step 1: Discover verses with citations across all chapters
    chapter_verse_tasks: List[Tuple[int, str, int, str]] = []

    def scan_chapter(item: Tuple[int, str, str, int]) -> List[Tuple[int, str, int, str]]:
        b_id, b_slug, b_name, ch = item
        found_verses = set()
        # Scan 1830-1930
        u1 = f"{BASE_URL}/Any/1830/1930/all/s/i/{b_id}/{ch}"
        try:
            r1 = session.get(u1, timeout=12)
            soup1 = BeautifulSoup(r1.text, "html.parser")
            for a in soup1.find_all("a"):
                oc = a.get("onclick", "")
                m = re.search(r"getFilter\('\d+',\s*'(\d+)',\s*'([^']+)'", oc)
                if m and m.group(1) == str(ch):
                    v_spec = m.group(2)
                    if v_spec.isdigit():
                        found_verses.add(v_spec)
        except Exception:
            pass

        # Scan TPJS
        u2 = f"{BASE_URL}/Any/1830/2026/T/s/i/{b_id}/{ch}"
        try:
            r2 = session.get(u2, timeout=12)
            soup2 = BeautifulSoup(r2.text, "html.parser")
            for a in soup2.find_all("a"):
                oc = a.get("onclick", "")
                m = re.search(r"getFilter\('\d+',\s*'(\d+)',\s*'([^']+)'", oc)
                if m and m.group(1) == str(ch):
                    v_spec = m.group(2)
                    if v_spec.isdigit():
                        found_verses.add(v_spec)
        except Exception:
            pass

        return [(b_id, b_slug, ch, v) for v in sorted(found_verses, key=int)]

    scan_tasks = []
    for b_id, b_slug, b_name, num_ch in BOM_BOOKS:
        for ch in range(1, num_ch + 1):
            scan_tasks.append((b_id, b_slug, b_name, ch))

    with ThreadPoolExecutor(max_workers=10) as ex:
        results = ex.map(scan_chapter, scan_tasks)
        for sublist in results:
            chapter_verse_tasks.extend(sublist)

    logger.info(
        f"Found {len(chapter_verse_tasks)} verses with early citations. Fetching citation details..."
    )

    # Step 2: Fetch citations for each verse
    all_citations: Dict[str, List[Citation]] = {}

    def worker(task: Tuple[int, str, int, str]) -> Tuple[str, List[Citation]]:
        b_id, b_slug, ch, v_str = task
        return fetch_verse_citations(b_id, b_slug, ch, v_str, session)

    with ThreadPoolExecutor(max_workers=12) as ex:
        verse_results = ex.map(worker, chapter_verse_tasks)
        for v_key, cits in verse_results:
            if cits:
                all_citations[v_key] = cits

    # Deduplicate citations to last verse
    all_citations = deduplicate_citations_to_last_verse(all_citations)


    # Serialize to cache
    serialized = {
        v_key: [c.to_dict() for c in cits] for v_key, cits in all_citations.items()
    }
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)

    logger.info(
        f"Successfully fetched, deduplicated, and cached citations for {len(all_citations)} verses to {cache_path}"
    )
    return all_citations

