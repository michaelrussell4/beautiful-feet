"""Strip all Deseret Alphabet characters and references from data/onomasticon.json."""

import json
import re
import os

ONOMA_PATH = "data/onomasticon.json"

with open(ONOMA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

deseret_char_pattern = re.compile(r"[\U00010400-\U0001044F]")
deseret_phrase_pattern = re.compile(r"Deseret Alphabet\s*:\s*[\U00010400-\U0001044F\s]+(?:\([^)]*\))?", re.IGNORECASE)

cleaned_entries = 0

prose_replacements = [
    (
        r"the Deseret Alphabet transcriptions are identical",
        "their historical phonetic transcriptions are identical",
    ),
    (
        r"according to the Deseret Alphabet spelling, has",
        "in historical phonetic transcription, has",
    ),
    (
        r"and the Deseret Alphabet spelling of the PN [A-Z ]+,*\s*(?:\(IPA:[^)]+\),*\s*)*(?:and,*\s*(?:\(IPA:[^)]+\),*\s*)*)?suggest",
        "and historical phonetic transcriptions (IPA) suggest",
    ),
    (
        r"as ɒmnɛr in the 1869 Deseret Alphabet; amner in SBL transliteration; IPA = ͻmnɛr",
        "amner in SBL transliteration; IPA = /ͻmnɛr/",
    ),
    (
        r"according to the Deseret Alphabet spelling also begins",
        "in historical phonetic transcription also begins",
    ),
]

def clean_entry_text(text: str) -> str:
    for pat, rep in prose_replacements:
        text = re.sub(pat, rep, text, flags=re.I)
    text = deseret_phrase_pattern.sub("", text)
    text = deseret_char_pattern.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text

for lemma, entry in data.items():
    had_des = False
    if entry.get("deseret"):
        entry["deseret"] = ""
        had_des = True

    # Clean summary
    summary = entry.get("summary", "")
    if deseret_char_pattern.search(summary) or "Deseret Alphabet" in summary:
        entry["summary"] = clean_entry_text(summary)
        had_des = True

    # Clean etymology paragraphs
    paras = entry.get("etymology_paragraphs", [])
    cleaned_paras = []
    for p in paras:
        if deseret_char_pattern.search(p) or "Deseret Alphabet" in p:
            p = clean_entry_text(p)
            had_des = True
        if p:
            cleaned_paras.append(p)
    entry["etymology_paragraphs"] = cleaned_paras

    if had_des:
        cleaned_entries += 1

with open(ONOMA_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Cleaned {cleaned_entries} entries in {ONOMA_PATH}.")

# Verify
with open(ONOMA_PATH, "r", encoding="utf-8") as f:
    verify_text = f.read()
remaining = len(deseret_char_pattern.findall(verify_text))
print(f"Remaining Deseret characters in {ONOMA_PATH}: {remaining}")
assert remaining == 0, f"Expected 0 remaining Deseret characters, got {remaining}"
