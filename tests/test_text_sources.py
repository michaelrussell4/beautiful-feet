"""Unit tests for Book of Mormon scripture text sources (modern and 1830 first edition)."""

import json
import os
import pytest

from beautiful_feet.text_parser import parse_book_of_mormon_md

EXPECTED_CANONICAL_BOOKS = [
    "First Book of Nephi",
    "Second Book of Nephi",
    "The Book of Jacob",
    "The Book of Enos",
    "The Book of Jarom",
    "The Book of Omni",
    "The Words of Mormon",
    "The Book of Mosiah",
    "The Book of Alma",
    "The Book of Helaman",
    "Third Book of Nephi",
    "Fourth Book of Nephi",
    "The Book of Mormon",
    "The Book of Ether",
    "The Book of Moroni",
]


@pytest.fixture(scope="module")
def modern_books():
    """Load and parse the base modern scripture text."""
    return parse_book_of_mormon_md("assets/raw/Book of Mormon.md")


@pytest.fixture(scope="module")
def bom_1830():
    """Load the 1830 Palmyra first edition dataset."""
    path = "data/bom_1830.json"
    assert os.path.exists(path), f"Missing 1830 text file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_1830_text_source_integrity(bom_1830):
    """Verify 1830 first edition dataset contains all 6,604 verses with valid content."""
    assert len(bom_1830) == 6604, f"Expected 6604 verses in 1830 dataset, found {len(bom_1830)}"
    for key, text in bom_1830.items():
        assert isinstance(key, str) and len(key) > 0, f"Invalid key: {key}"
        assert isinstance(text, str) and len(text.strip()) > 0, f"Empty text for key: {key}"


def test_modern_text_parser_integrity(modern_books):
    """Verify parsed modern text contains all 15 books, 239 chapters, and 6,604 verses."""
    assert len(modern_books) == 15
    titles = [b.title for b in modern_books]
    assert titles == EXPECTED_CANONICAL_BOOKS

    total_chapters = sum(len(b.chapters) for b in modern_books)
    assert total_chapters == 239, f"Expected 239 chapters, got {total_chapters}"

    total_verses = sum(len(c.verses) for b in modern_books for c in b.chapters)
    assert total_verses == 6604, f"Expected 6604 verses, got {total_verses}"


def test_verse_key_parity_between_modern_and_1830(modern_books, bom_1830):
    """Verify exact 1-to-1 verse key mapping parity between modern and 1830 editions."""
    modern_keys = {
        v.verse_key
        for b in modern_books
        for c in b.chapters
        for v in c.verses
    }
    keys_1830 = set(bom_1830.keys())

    missing_in_1830 = modern_keys - keys_1830
    extra_in_1830 = keys_1830 - modern_keys

    assert len(missing_in_1830) == 0, f"Modern keys missing in 1830 dataset: {missing_in_1830}"
    assert len(extra_in_1830) == 0, f"Extra keys in 1830 dataset: {extra_in_1830}"
    assert modern_keys == keys_1830


def test_landmark_verses_present(modern_books, bom_1830):
    """Verify famous landmark textual differences exist in the source texts."""
    modern_map = {
        v.verse_key: v.text
        for b in modern_books
        for c in b.chapters
        for v in c.verses
    }

    # 1. 1 Nephi 11:18 - "mother of God" (1830) vs "mother of the Son of God" (modern)
    t1830 = bom_1830["1-ne-11-18"]
    tmod = modern_map["1-ne-11-18"]
    assert "mother of God" in t1830
    assert "mother of the Son of God" in tmod

    # 2. 1 Nephi 11:21 - "even the Eternal Father" (1830) vs "even the Son of the Eternal Father" (modern)
    t1830 = bom_1830["1-ne-11-21"]
    tmod = modern_map["1-ne-11-21"]
    assert "even the Eternal Father" in t1830
    assert "even the Son of the Eternal Father" in tmod

    # 3. Mosiah 21:28 - "king Benjamin" (1830) vs "king Mosiah" (modern)
    t1830 = bom_1830["mosiah-21-28"]
    tmod = modern_map["mosiah-21-28"]
    assert "Benjamin" in t1830
    assert "Mosiah" in tmod

    # 4. 2 Nephi 30:6 - "white and a delightsome" (1830) vs "pure and a delightsome" (modern)
    t1830 = bom_1830["2-ne-30-6"]
    tmod = modern_map["2-ne-30-6"]
    assert "white" in t1830
    assert "pure" in tmod
