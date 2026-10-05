"""Fetcher and parser for Book of Mormon Onomasticon."""

from __future__ import annotations
import os
import re
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional
import requests
from bs4 import BeautifulSoup

from .models import OnomaEntry

logger = logging.getLogger(__name__)

BASE_URL = "https://onoma.lib.byu.edu/api.php"


def get_all_name_titles(session: Optional[requests.Session] = None) -> List[str]:
    """Retrieve all lemmas from Category:Names on the Onomasticon."""
    s = session or requests.Session()
    all_names = []
    cmcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Names",
            "cmlimit": "500",
            "format": "json",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        resp = s.get(BASE_URL, params=params, timeout=15).json()
        members = resp.get("query", {}).get("categorymembers", [])
        all_names.extend(members)
        if "continue" in resp and "cmcontinue" in resp["continue"]:
            cmcontinue = resp["continue"]["cmcontinue"]
        else:
            break
    return [m["title"] for m in all_names]


def clean_lemma(title: str) -> str:
    """Clean lemma name, stripping leading asterisks, parenthesis suffixes, etc."""
    lemma = title.lstrip("*").strip()
    # Normalize suffixes like ZORAMITE(S) -> Zoramites / Zoramite
    # But preserve canonical title e.g. Nephi, Zarahemla
    return lemma


def to_title_case_name(name: str) -> str:
    """Format ALL-CAPS lemma to Title Case, e.g. NEPHI -> Nephi, ZARAHEMLA -> Zarahemla."""
    # Special cases with hyphens or apostrophes
    parts = name.split("-")
    titled_parts = []
    for part in parts:
        if part.upper().startswith("MC"):
            titled_parts.append("Mc" + part[2:].capitalize())
        else:
            titled_parts.append(part.capitalize())
    return "-".join(titled_parts)


def parse_onoma_page(title: str, session: Optional[requests.Session] = None) -> Optional[OnomaEntry]:
    """Parse raw page content from Onomasticon into structured OnomaEntry."""
    s = session or requests.Session()
    try:
        r = s.get(
            BASE_URL,
            params={"action": "parse", "page": title, "prop": "text", "format": "json"},
            timeout=15,
        )
        html = r.json().get("parse", {}).get("text", {}).get("*", "")
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # 1. Classification & Definition from table
        classification = ""
        definition = ""
        table = soup.find("table", class_="wikitable")
        if table:
            tds = table.find_all("td")
            if tds:
                classification = tds[0].get_text(" ", strip=True)
                classification = re.sub(r"\s+", " ", classification)
                if len(tds) > 1:
                    def_parts = [td.get_text(" ", strip=True) for td in tds[1:]]
                    definition = " ".join(def_parts)
                    definition = re.sub(r"\s+", " ", definition)

        # 2. Deseret alphabet & Pronunciation (IPA)
        deseret = ""
        pronunciation = ""

        # Check Deseret characters
        m_des = re.findall(r"([𐐀-𐑏]+)", html)
        if m_des:
            deseret = m_des[0]

        # Check IPA in parentheses with Deseret, e.g. 𐐤𐐀𐐙𐐌 (niːfaɪ)
        m_pron_des = re.findall(r"[𐐀-𐑏]+\s*(?:,\s*)?\((?:IPA\s*)?/?([^/)]+)/?\)", html)
        if m_pron_des:
            pronunciation = m_pron_des[0].strip()

        if not pronunciation:
            m_ipa = re.search(r"\(IPA\s+/?([^/)]+)/?\)", html)
            if not m_ipa:
                m_ipa = re.search(r"IPA\s+/?([^/\s<,]+)/?", html)
            if not m_ipa:
                m_ipa = re.search(r"/([a-zæɑɔəɛɪʊʌθðʃʒŋʔːˈˌ]{3,20})/", html)
            if m_ipa:
                pronunciation = m_ipa.group(1).strip()

        # 3. Etymology Summary
        etym_paras = []
        etym_header = soup.find(
            lambda tag: tag.name in ["h2", "h3", "p", "b"] and "Etymology" in tag.get_text()
        )
        if etym_header:
            curr = etym_header.parent if etym_header.name == "b" else etym_header
            curr = curr.find_next_sibling()
            while curr and len(etym_paras) < 3:
                if curr.name in ["h2", "h3"]:
                    break
                if curr.name == "p":
                    txt = curr.get_text(" ", strip=True)
                    txt = re.sub(r"\[\d+\]", "", txt)  # remove [1], [2]
                    txt = re.sub(r"\s+", " ", txt)
                    if (
                        len(txt) > 25
                        and not txt.startswith("Jump to navigation")
                        and not txt.startswith("Contents")
                    ):
                        etym_paras.append(txt)
                curr = curr.find_next_sibling()

        summary = " ".join(etym_paras[:2])
        if not summary:
            for p in soup.find_all("p"):
                txt = p.get_text(" ", strip=True)
                txt = re.sub(r"\[\d+\]", "", txt)
                txt = re.sub(r"\s+", " ", txt)
                if len(txt) > 30 and not txt.startswith("Jump to navigation"):
                    summary = txt
                    break

        cleaned = clean_lemma(title)
        return OnomaEntry(
            lemma=cleaned,
            raw_title=title,
            classification=classification,
            definition=definition,
            deseret=deseret,
            pronunciation=pronunciation,
            summary=summary,
            etymology_paragraphs=etym_paras,
        )
    except Exception as e:
        logger.warning(f"Error parsing onomasticon entry {title}: {e}")
        return None


def fetch_all_onomasticon(
    cache_path: str = "data/onomasticon.json", force_refresh: bool = False
) -> Dict[str, OnomaEntry]:
    """Fetch complete onomasticon or load from cache."""
    if os.path.exists(cache_path) and not force_refresh:
        logger.info(f"Loading onomasticon from cache: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: OnomaEntry.from_dict(v) for k, v in data.items()}

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    logger.info("Fetching Onomasticon lemmas from BYU API...")
    titles = get_all_name_titles()
    logger.info(f"Found {len(titles)} names. Fetching full records...")

    entries: Dict[str, OnomaEntry] = {}
    with requests.Session() as s:
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(parse_onoma_page, t, s) for t in titles]
            for fut in futures:
                res = fut.result()
                if res:
                    entries[res.lemma.upper()] = res

    # Write cache
    serialized = {k: v.to_dict() for k, v in entries.items()}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)

    logger.info(f"Successfully cached {len(entries)} Onomasticon entries to {cache_path}")
    return entries
