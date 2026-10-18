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


def _clean_onoma_text(txt: str) -> str:
    txt = re.sub(r"\[\s*\d+\s*\]", "", txt)  # remove [1], [ 12 ], etc.
    txt = re.sub(r"Deseret Alphabet\s*:\s*[^\s.]+(?:\s*\([^)]*\))?", "", txt, flags=re.I)
    txt = re.sub(r"the Deseret Alphabet transcriptions are identical", "their historical phonetic transcriptions are identical", txt, flags=re.I)
    txt = re.sub(r"according to the Deseret Alphabet spelling, has", "in historical phonetic transcription, has", txt, flags=re.I)
    txt = re.sub(
        r"and the Deseret Alphabet spelling of the PN [A-Z ]+,*\s*(?:\(IPA:[^)]+\),*\s*)*(?:and,*\s*(?:\(IPA:[^)]+\),*\s*)*)?suggest",
        "and historical phonetic transcriptions (IPA) suggest",
        txt,
        flags=re.I,
    )
    txt = re.sub(
        r"as ɒmnɛr in the 1869 Deseret Alphabet; amner in SBL transliteration; IPA = ͻmnɛr",
        "amner in SBL transliteration; IPA = /ͻmnɛr/",
        txt,
        flags=re.I,
    )
    txt = re.sub(r"according to the Deseret Alphabet spelling also begins", "in historical phonetic transcription also begins", txt, flags=re.I)
    txt = re.sub(r"[\U00010400-\U0001044F]+", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    txt = re.sub(r"\s+([.,;:!?])", r"\1", txt)
    return txt


def parse_onoma_page(title: str, session: Optional[requests.Session] = None) -> Optional[OnomaEntry]:
    """Parse raw page content from Onomasticon into structured OnomaEntry."""
    s = session or requests.Session()
    try:
        r = s.get(
            BASE_URL,
            params={"action": "parse", "page": title, "prop": "text", "format": "json", "redirects": 1},
            timeout=15,
        )
        data = r.json()
        html = data.get("parse", {}).get("text", {}).get("*", "")
        if not html:
            return None

        # Check for cross-reference like "This name is treated under <a ...>NAME</a>"
        m_treated = re.search(r"treated under\s*<a\s+[^>]*title=[\"']([^\"']+)[\"']", html, re.I)
        if m_treated:
            target = m_treated.group(1)
            r = s.get(
                BASE_URL,
                params={"action": "parse", "page": target, "prop": "text", "format": "json", "redirects": 1},
                timeout=15,
            )
            html = r.json().get("parse", {}).get("text", {}).get("*", "") or html

        soup = BeautifulSoup(html, "html.parser")

        # 1. Classification from table (list of distinct types of entities)
        classes = []
        table = soup.find("table", class_="wikitable")
        if table:
            for tr in table.find_all("tr"):
                tds = tr.find_all(["td", "th"])
                if not tds:
                    continue
                txt = tds[0].get_text(" ", strip=True)
                txt = re.sub(r"\s+", " ", txt).strip()
                if txt and not re.match(r"^\d+\.?$", txt) and txt not in classes:
                    classes.append(txt)
        classification = ", ".join(classes)
        # We deliberately do not store exhaustive scriptural citations from the table as definition
        definition = ""

        # 2. Pronunciation (IPA)
        deseret = ""
        pronunciation = ""

        m_des = re.search(r"[\U00010400-\U0001044F]+\s*\(([a-zæɑɔəɛɪʊʌθðʃʒŋʔːˈˌ\s/]+)\)", html)
        if m_des:
            pronunciation = m_des.group(1).strip().strip("/")
        if not pronunciation:
            m_ipa = re.search(r"\(IPA:\s*(?:<i>)?([a-zæɑɔəɛɪʊʌθðʃʒŋʔːˈˌ/]+)", html)
            if m_ipa:
                pronunciation = m_ipa.group(1).strip().strip("/")
        if not pronunciation:
            m_pron = re.findall(r"\((?:IPA\s*)?/?([a-zæɑɔəɛɪʊʌθðʃʒŋʔːˈˌ]{3,25})/?\)", html)
            for cand in m_pron:
                if cand.lower() not in ["passive", "active", "plural", "singular"]:
                    pronunciation = cand.strip().strip("/")
                    break
        if not pronunciation:
            m_slash = re.search(r"/([a-zæɑɔəɛɪʊʌθðʃʒŋʔːˈˌ]{3,20})/", html)
            if m_slash:
                pronunciation = m_slash.group(1).strip().strip("/")

        # 3. Etymology Paragraphs
        etym_paras = []
        stop_re = re.compile(
            r"^(variants|notes|bibliography|references|see also|external links|name index|key to abbreviations)",
            re.I,
        )
        etym_header = soup.find(
            lambda tag: tag.name in ["h2", "h3", "p", "b"] and "Etymology" in tag.get_text()
        )
        curr = None
        if etym_header:
            curr = etym_header.parent if etym_header.name == "b" else etym_header
            curr = curr.find_next_sibling()
        elif table:
            curr = table.find_next_sibling()

        while curr:
            tag_name = curr.name
            if tag_name in ["h2", "h3", "h4"]:
                break
            if tag_name == "p":
                clean_p = curr.get_text(" ", strip=True)
                if stop_re.match(clean_p) and len(clean_p) < 40:
                    break
                txt = _clean_onoma_text(clean_p)
                if (
                    len(txt) > 5
                    and not txt.startswith("Jump to navigation")
                    and not txt.startswith("Contents")
                ):
                    etym_paras.append(txt)
            elif tag_name in ["ol", "ul"] and "references" in curr.get("class", []):
                break
            curr = curr.find_next_sibling()

        summary = "\n\n".join(etym_paras)

        cleaned = clean_lemma(title)
        return OnomaEntry(
            lemma=cleaned,
            raw_title=title,
            classification=classification,
            definition=definition,
            deseret="",
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
