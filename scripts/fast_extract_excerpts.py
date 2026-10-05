"""Fast, vectorized excerpt extraction grouping citations by talk_id."""

import os
import sys
import re
import json
import time
from typing import Dict, List, Set, Tuple
from bs4 import BeautifulSoup
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CACHE_DIR = "data/talks_cache"
RAW_METADATA_FILE = "scratch/citations_raw_metadata.json"
OUTPUT_FILE = "data/early_citations.json"


def clean_text_unicode(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r'([a-zA-Z])\ufffd([a-zA-Z])', r'\1’\2', text)
    text = re.sub(r'(?:^|\s)\ufffd([a-zA-Z])', r' “\1', text)
    text = re.sub(r'([a-zA-Z.,!?])\ufffd(?:\s|$)', r'\1” ', text)
    text = re.sub(r'\s*\ufffd\s*', ' — ', text)
    text = text.replace('\ufffd', '’')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_paragraph_text(el) -> str:
    if not el:
        return ""
    # Shallow copy or clean via text
    txt = el.get_text(" ", strip=True)
    # Remove bracketed page markers like [ p. 48b] or [ p. 49a]
    txt = re.sub(r"\[\s*p\.\s*[\d\w]+\s*\]", "", txt)
    return clean_text_unicode(txt)


def main():
    print("Loading raw citations metadata...")
    t0 = time.time()
    with open(RAW_METADATA_FILE, "r", encoding="utf-8") as f:
        all_cits: Dict[str, List[dict]] = json.load(f)

    total_citations = sum(len(c_list) for c_list in all_cits.values())
    print(f"Loaded {len(all_cits)} verses, {total_citations} citations in {time.time() - t0:.2f}s.")

    # Group citation references by talk_id
    talk_targets: Dict[str, List[Tuple[str, int, str]]] = defaultdict(list)
    for vk, c_list in all_cits.items():
        for idx, c in enumerate(c_list):
            tid = c.get("talk_id", "").strip()
            tgt = c.get("target_id", "").strip()
            if tid and tgt:
                talk_targets[tid].append((vk, idx, tgt))

    print(f"Grouped into {len(talk_targets)} unique discourses to parse.")

    t_start_parse = time.time()
    excerpts_found = 0
    parsed_talks = 0

    for tid, target_list in talk_targets.items():
        path = os.path.join(CACHE_DIR, f"{tid}.html")
        if not os.path.exists(path):
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                html_str = f.read()
        except Exception:
            continue

        if not html_str:
            continue

        # Parse HTML once per talk using lxml (very fast)
        try:
            soup = BeautifulSoup(html_str, "lxml")
        except Exception:
            soup = BeautifulSoup(html_str, "html.parser")

        # Map targets
        for vk, idx, tgt in target_list:
            target = soup.find(id=tgt)
            if not target:
                continue

            excerpt = ""
            # Strategy 1: Journal of Discourses / General Conference
            p_div = target.find_parent(class_=re.compile(r"paragraph|std|jodcontent"))
            if p_div:
                curr_text = clean_paragraph_text(p_div)
                if curr_text:
                    if len(curr_text) >= 450:
                        excerpt = curr_text
                    else:
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
                        excerpt = "\n\n".join(paras)

            # Strategy 2: TPJS (footnote target)
            if not excerpt:
                fn_div = target.find_parent(class_=re.compile(r"footnote"))
                if fn_div:
                    fn_match = re.match(r"^\s*(\d+)\.", fn_div.get_text())
                    fn_num = fn_match.group(1) if fn_match else ""
                    page_div = target.find_parent(class_=re.compile(r"page|talkcontent"))
                    if page_div:
                        for p in page_div.find_all(["p", "div"], class_=re.compile(r"std|cont|paragraph")):
                            p_text = clean_paragraph_text(p)
                            if fn_num and re.search(rf"\b{fn_num}\b", p.get_text()):
                                excerpt = p_text
                                break
                        if not excerpt:
                            for p in page_div.find_all("p", class_="std"):
                                excerpt = clean_paragraph_text(p)
                                break

            if excerpt:
                all_cits[vk][idx]["excerpt"] = excerpt
                excerpts_found += 1

        parsed_talks += 1
        if parsed_talks % 100 == 0 or parsed_talks == len(talk_targets):
            print(f"  Parsed {parsed_talks}/{len(talk_targets)} talks ({time.time() - t_start_parse:.2f}s, {excerpts_found} excerpts extracted)")

    print(f"\nExtraction complete in {time.time() - t_start_parse:.2f}s!")
    print(f"  Total citations: {total_citations}")
    print(f"  Citations with verbatim discourse excerpts: {excerpts_found} ({excerpts_found/total_citations*100:.1f}%)")

    # Save to data/early_citations.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_cits, f, indent=2, ensure_ascii=False)
    print(f"Saved enriched data to {OUTPUT_FILE} (size: {os.path.getsize(OUTPUT_FILE)/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()
