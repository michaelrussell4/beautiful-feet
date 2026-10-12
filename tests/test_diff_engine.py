"""Unit tests for the 1830 revision diff engine and verse revision generation."""

import xml.etree.ElementTree as ET
import pytest

from beautiful_feet.tagger import generate_verse_revision


def test_identical_verse_produces_no_diff_tags():
    """Verses with identical wording should return clean text with no <del> or <ins> tags."""
    t_1830 = "And it came to pass that I, Nephi, did return."
    t_mod = "And it came to pass that I, Nephi, did return."
    rev = generate_verse_revision(t_1830, t_mod)
    assert "<del" not in rev
    assert "<ins" not in rev
    assert rev == "And it came to pass that I, Nephi, did return."


def test_punctuation_differences_are_ignored():
    """Typesetter punctuation variations (commas, semicolons, dashes) should not trigger diffs."""
    t_1830 = "And now, I Lehi, say unto you; hear my words!"
    t_mod = "And now I, Lehi, say unto you: hear my words!"
    rev = generate_verse_revision(t_1830, t_mod)
    assert "<del" not in rev
    assert "<ins" not in rev
    # Preserves modern punctuation
    assert rev == "And now I, Lehi, say unto you: hear my words!"


def test_capitalization_differences_preserve_modern():
    """Capitalization differences should match words as equal and preserve the modern case."""
    t_1830 = "and it came to pass that god spake unto him."
    t_mod = "And it came to pass that God spake unto him."
    rev = generate_verse_revision(t_1830, t_mod)
    assert "<del" not in rev
    assert "<ins" not in rev
    assert rev == "And it came to pass that God spake unto him."


def test_word_replacement():
    """Word substitutions should wrap 1830 in <del class='diff-1830'> and modern in <ins class='diff-modern'>."""
    t_1830 = "And king Benjamin had a gift from God."
    t_mod = "And king Mosiah had a gift from God."
    rev = generate_verse_revision(t_1830, t_mod)
    assert '<del class="diff-1830">Benjamin</del> <ins class="diff-modern">Mosiah</ins>' in rev
    # Valid XML check
    el = ET.fromstring(f"<p>{rev}</p>")
    assert el.find("del").text == "Benjamin"
    assert el.find("ins").text == "Mosiah"


def test_word_insertion():
    """Words added in the modern text should be wrapped in <ins class='diff-modern'>."""
    t_1830 = "Behold, the virgin is the mother of God."
    t_mod = "Behold, the virgin is the mother of the Son of God."
    rev = generate_verse_revision(t_1830, t_mod)
    assert '<ins class="diff-modern">the Son of</ins>' in rev
    assert "<del" not in rev
    ET.fromstring(f"<p>{rev}</p>")


def test_word_deletion():
    """Words deleted in the modern text should be wrapped in <del class='diff-1830'>."""
    t_1830 = "And they were exceedingly angry with them, which were in the wilderness."
    t_mod = "And they were exceedingly angry with them."
    rev = generate_verse_revision(t_1830, t_mod)
    assert '<del class="diff-1830">which were in the wilderness</del>' in rev
    ET.fromstring(f"<p>{rev}</p>")


def test_punctuation_attachment_eliminates_floating_space():
    """Punctuation following an insertion or replacement should attach cleanly without a gap."""
    t_1830 = "And king Benjamin, who was righteous."
    t_mod = "And king Mosiah, who was righteous."
    rev = generate_verse_revision(t_1830, t_mod)
    # The comma should attach directly to the closing tag </ins>,
    assert "</ins>," in rev
    assert "</ins> ," not in rev
    ET.fromstring(f"<p>{rev}</p>")


def test_xml_escaping_in_diff_text():
    """Ensure characters like &, <, > are safely escaped while apostrophes remain clean."""
    t_1830 = "Nephi's brother Sam & Jacob <beloved>."
    t_mod = "Nephi's brother Sam & Jacob <faithful>."
    rev = generate_verse_revision(t_1830, t_mod)
    assert "&amp;" in rev
    assert "&lt;" in rev
    assert "&gt;" in rev
    assert "Nephi's" in rev
    # Ensure it parses as strictly valid XML
    ET.fromstring(f"<p>{rev}</p>")


def test_all_6604_verses_generate_valid_xml():
    """Batch test all 6,604 verses against 1830 text to ensure zero XML syntax errors."""
    import json
    from beautiful_feet.text_parser import parse_book_of_mormon_md

    with open("data/bom_1830.json", "r", encoding="utf-8") as f:
        bom_1830 = json.load(f)

    books = parse_book_of_mormon_md("assets/raw/Book of Mormon.md")
    total_tested = 0
    diff_count = 0

    for book in books:
        for ch in book.chapters:
            for v in ch.verses:
                total_tested += 1
                t_1830 = bom_1830[v.verse_key]
                rev = generate_verse_revision(t_1830, v.text)
                if "<del" in rev or "<ins" in rev:
                    diff_count += 1
                # Must parse cleanly as an XML element
                try:
                    ET.fromstring(f"<p>{rev}</p>")
                except Exception as exc:
                    pytest.fail(f"XML parse failure in {v.verse_key}: {exc}\nText: {rev}")

    assert total_tested == 6604
    assert diff_count > 3000, f"Expected >3000 verses with revisions, got {diff_count}"
