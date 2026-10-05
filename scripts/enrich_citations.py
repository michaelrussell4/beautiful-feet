"""Full pipeline to enrich Book of Mormon citations with talk IDs, target IDs, and verbatim discourse excerpts."""

import os
import sys
import re
import json
import time
from typing import Dict, List, Set, Tuple, Optional
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CACHE_DIR = "data/talks_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
RAW_METADATA_FILE = "scratch/citations_raw_metadata.json"
OUTPUT_FILE = "data/early_citations.json"

SLUG_TO_ID = {
    "1-ne": 205, "2-ne": 206, "jacob": 207, "enos": 208, "jarom": 209,
    "omni": 210, "w-of-m": 211, "mosiah": 212, "alma": 213, "hel": 214,
    "3-ne": 215, "4-ne": 216, "morm": 217, "ether": 218, "moroni": 219,
}

JD_VOLUME_YEARS: Dict[int, int] = {
    1: 1854, 2: 1855, 3: 1856, 4: 1857, 5: 1858, 6: 1859, 7: 1860, 8: 1861,
    9: 1862, 10: 1865, 11: 1867, 12: 1869, 13: 1871, 14: 1872, 15: 1873,
    16: 1874, 17: 1875, 18: 1877, 19: 1878, 20: 1880, 21: 1881, 22: 1882,
    23: 1883, 24: 1884, 25: 1885, 26: 1886,
}


def clean_text_unicode(text: str) -> str:
    """Clean unprintable or corrupted characters (\ufffd, non-breaking spaces)."""
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    # Replace \ufffd between letters with apostrophe
    text = re.sub(r'([a-zA-Z])\ufffd([a-zA-Z])', r'\1’\2', text)
    # Replace \ufffd before words with left quote
    text = re.sub(r'(?:^|\s)\ufffd([a-zA-Z])', r' “\1', text)
    # Replace \ufffd after punctuation/words with right quote
    text = re.sub(r'([a-zA-Z.,!?])\ufffd(?:\s|$)', r'\1” ', text)
    # Replace \ufffd between spaces with em-dash
    text = re.sub(r'\s*\ufffd\s*', ' — ', text)
    # Replace any remaining \ufffd
    text = text.replace('\ufffd', '’')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_ref_item(ref_text: str) -> Optional[Tuple[str, str, str, Optional[int]]]:
    ref_text = ref_text.strip()
    m_jd = re.match(r"^JD\s+(\d+):([\d\w]+)(?:,\s*(.+))?$", ref_text, re.I)
    if m_jd:
        vol = int(m_jd.group(1))
        page = m_jd.group(2)
        speaker = clean_text_unicode((m_jd.group(3) or "").strip())
        year = JD_VOLUME_YEARS.get(vol)
        return speaker, "Journal of Discourses", f"JD {vol}:{page}", year

    m_tpjs = re.match(r"^TPJS\s+([\d\w]+)(?:,\s*(.+))?$", ref_text, re.I)
    if m_tpjs:
        page = m_tpjs.group(1)
        speaker = clean_text_unicode((m_tpjs.group(2) or "Joseph Smith").strip())
        return speaker, "Teachings of the Prophet Joseph Smith", f"TPJS {page}", None

    m_hc = re.match(r"^HC\s+(\d+):([\d\w]+)(?:,\s*(.+))?$", ref_text, re.I)
    if m_hc:
        vol = int(m_hc.group(1))
        page = m_hc.group(2)
        speaker = clean_text_unicode((m_hc.group(3) or "Joseph Smith").strip())
        return speaker, "History of the Church", f"HC {vol}:{page}", None

    m_ts = re.match(r"^TS\s+(\d+):([\d\w]+)(?:,\s*(.+))?$", ref_text, re.I)
    if m_ts:
        vol = int(m_ts.group(1))
        page = m_ts.group(2)
        speaker = clean_text_unicode((m_ts.group(3) or "").strip())
        return speaker, "Times and Seasons", f"TS {vol}:{page}", None

    m_ms = re.match(r"^MS\s+(\d+):([\d\w]+)(?:,\s*(.+))?$", ref_text, re.I)
    if m_ms:
        vol = int(m_ms.group(1))
        page = m_ms.group(2)
        speaker = clean_text_unicode((m_ms.group(3) or "").strip())
        return speaker, "Millennial Star", f"MS {vol}:{page}", None

    return None


def fetch_verse_raw_citations(task: Tuple[int, str, str, str]) -> Tuple[str, List[dict]]:
    b_id, b_slug, ch, v = task
    verse_key = f"{b_slug}-{ch}-{v}"
    cits = []
    seen = set()

    for corpus, url_pattern in [
        ("all", f"https://scriptures.byu.edu/citation_index/citation_ajax/Any/1830/1900/all/s/i/{b_id}/{ch}?verses={v}"),
        ("T", f"https://scriptures.byu.edu/citation_index/citation_ajax/Any/1830/2026/T/s/i/{b_id}/{ch}?verses={v}"),
    ]:
        try:
            r = requests.get(url_pattern, timeout=14)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for li in soup.find_all("li"):
                ref = li.find(class_="reference")
                talk = li.find(class_="talktitle")
                a = li.find("a")
                if not ref or not a:
                    continue
                parsed = parse_ref_item(ref.get_text(" ", strip=True))
                if not parsed:
                    continue
                speaker, source, cit_str, year = parsed
                talk_title = clean_text_unicode(talk.get_text(" ", strip=True) if talk else "")

                talk_id = ""
                target_id = ""
                oc = a.get("onclick", "")
                m = re.search(r"getTalk\('(\d+)',\s*'(\d+)'\)", oc)
                if m:
                    talk_id = m.group(1)
                    target_id = m.group(2)

                sig = (source, cit_str, speaker)
                if sig not in seen:
                    seen.add(sig)
                    cits.append({
                        "speaker": speaker,
                        "source": source,
                        "citation": cit_str,
                        "year": year,
                        "talk_title": talk_title,
                        "talk_id": talk_id,
                        "target_id": target_id,
                        "excerpt": "",
                    })
        except Exception:
            pass

    return verse_key, cits


def fetch_talk_html(talk_id: str, session: Optional[requests.Session] = None) -> str:
    path = os.path.join(CACHE_DIR, f"{talk_id}.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    url = f"https://scriptures.byu.edu/content/talks_ajax/{talk_id}"
    req_func = session.get if session else requests.get
    try:
        resp = req_func(url, timeout=15)
        if resp.status_code == 200:
            with open(path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            return resp.text
    except Exception:
        pass
    return ""


def clean_paragraph_text(el) -> str:
    if not el:
        return ""
    c = BeautifulSoup(str(el), "html.parser")
    # Remove internal citation and counter links
    for tag in c.find_all(["span", "a"], class_=lambda cl: cl and any(k in cl for k in ["citation", "ccontainer", "refcounter"])):
        tag.decompose()
    txt = c.get_text(" ", strip=True)
    # Remove page brackets like [ p. 48b]
    txt = re.sub(r"\[\s*p\.\s*[\d\w]+\s*\]", "", txt)
    return clean_text_unicode(txt)


def extract_excerpt(html_content: str, target_id: str) -> str:
    if not html_content or not target_id:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    target = soup.find(id=target_id)
    if not target:
        return ""

    # Strategy 1: Journal of Discourses & General Conference
    p_div = target.find_parent(class_=re.compile(r"paragraph|std|jodcontent"))
    if p_div:
        curr_text = clean_paragraph_text(p_div)
        if not curr_text:
            return ""

        # If curr_text is already substantial (> 450 chars), return it directly
        if len(curr_text) >= 450:
            return curr_text

        # Otherwise grab preceding/succeeding paragraph for context
        prev_p = p_div.find_previous_sibling(class_=re.compile(r"paragraph|std"))
        next_p = p_div.find_next_sibling(class_=re.compile(r"paragraph|std"))

        prev_text = clean_paragraph_text(prev_p) if prev_p else ""
        next_text = clean_paragraph_text(next_p) if next_p else ""

        paras = []
        if prev_text and len(prev_text) < 400:
            paras.append(prev_text)
        paras.append(curr_text)
        if next_text and len(next_text) < 400:
            paras.append(next_text)

        return "\n\n".join(paras)

    # Strategy 2: TPJS (footnote target)
    fn_div = target.find_parent(class_=re.compile(r"footnote"))
    if fn_div:
        fn_match = re.match(r"^\s*(\d+)\.", fn_div.get_text())
        fn_num = fn_match.group(1) if fn_match else ""
        page_div = target.find_parent(class_=re.compile(r"page|talkcontent"))
        if page_div:
            for p in page_div.find_all(["p", "div"], class_=re.compile(r"std|cont|paragraph")):
                p_text = clean_paragraph_text(p)
                if fn_num and re.search(rf"\b{fn_num}\b", p.get_text()):
                    return p_text
            for p in page_div.find_all("p", class_="std"):
                return clean_paragraph_text(p)

    return ""


def main():
    print("=== Step 1: Loading Chapter Verse Tasks ===")
    with open("scratch/chapter_verse_list.json", "r") as f:
        ch_verses = json.load(f)

    tasks = []
    for ch_key, verses in ch_verses.items():
        parts = ch_key.rsplit("-", 1)
        b_slug = parts[0]
        ch = parts[1]
        b_id = SLUG_TO_ID.get(b_slug)
        if b_id:
            for v in verses:
                tasks.append((b_id, b_slug, ch, v))

    print(f"Total verse citation tasks: {len(tasks)}")

    # Check if raw metadata is already cached
    all_cits: Dict[str, List[dict]] = {}
    if os.path.exists(RAW_METADATA_FILE):
        print(f"Loading existing raw metadata from {RAW_METADATA_FILE}...")
        with open(RAW_METADATA_FILE, "r", encoding="utf-8") as f:
            all_cits = json.load(f)
    else:
        print(f"Fetching raw metadata for {len(tasks)} verses using 25 workers...")
        t0 = time.time()
        completed = 0
        with ThreadPoolExecutor(max_workers=25) as ex:
            future_to_task = {ex.submit(fetch_verse_raw_citations, t): t for t in tasks}
            for fut in as_completed(future_to_task):
                vk, c_list = fut.result()
                if c_list:
                    all_cits[vk] = c_list
                completed += 1
                if completed % 250 == 0 or completed == len(tasks):
                    elapsed = time.time() - t0
                    print(f"  [{completed}/{len(tasks)}] verses scanned ({elapsed:.1f}s, found {len(all_cits)} with citations)")

        print(f"Finished verse scan in {time.time() - t0:.1f}s.")
        with open(RAW_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(all_cits, f, indent=2, ensure_ascii=False)
        print(f"Saved raw metadata to {RAW_METADATA_FILE}")

    # Step 2: Identify unique talk IDs to download
    unique_talk_ids: Set[str] = set()
    total_citations = 0
    for vk, c_list in all_cits.items():
        for c in c_list:
            total_citations += 1
            if c.get("talk_id"):
                unique_talk_ids.add(c["talk_id"])

    print(f"\nTotal citations: {total_citations}")
    print(f"Unique talks required: {len(unique_talk_ids)}")

    missing_talks = [tid for tid in unique_talk_ids if not os.path.exists(os.path.join(CACHE_DIR, f"{tid}.html"))]
    print(f"Talks already cached: {len(unique_talk_ids) - len(missing_talks)}")
    print(f"Talks to download: {len(missing_talks)}")

    if missing_talks:
        print(f"Downloading {len(missing_talks)} talks with 20 workers...")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(fetch_talk_html, tid) for tid in missing_talks]
            done = 0
            for _ in as_completed(futures):
                done += 1
                if done % 100 == 0 or done == len(missing_talks):
                    print(f"  [{done}/{len(missing_talks)}] talks downloaded ({time.time() - t0:.1f}s)")

    # Step 3: Extract excerpts for every citation
    print("\nExtracting excerpts from cached talks...")
    t0 = time.time()
    talk_html_cache: Dict[str, str] = {}
    excerpts_found = 0

    for vk, c_list in all_cits.items():
        for c in c_list:
            tid = c.get("talk_id")
            tgt = c.get("target_id")
            if tid and tgt:
                if tid not in talk_html_cache:
                    path = os.path.join(CACHE_DIR, f"{tid}.html")
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            talk_html_cache[tid] = f.read()
                    else:
                        talk_html_cache[tid] = ""
                html_str = talk_html_cache.get(tid, "")
                excerpt = extract_excerpt(html_str, tgt)
                c["excerpt"] = excerpt
                if excerpt:
                    excerpts_found += 1

    print(f"Extracted {excerpts_found}/{total_citations} ({excerpts_found/total_citations*100:.1f}%) verbatim excerpts in {time.time() - t0:.2f}s.")

    # Save to data/early_citations.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_cits, f, indent=2, ensure_ascii=False)
    print(f"Successfully saved enriched citations to {OUTPUT_FILE} (size: {os.path.getsize(OUTPUT_FILE)/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()
