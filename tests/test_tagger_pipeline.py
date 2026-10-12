"""Unit tests for the tagger pipeline (RevisionTagger, OnomaMatcher, VariantTagger, CitationTagger)."""

import json
import re
import xml.etree.ElementTree as ET
import pytest

from beautiful_feet.models import Chapter, Verse, OnomaEntry, Citation, TextualVariant
from beautiful_feet.tagger import (
    RevisionTagger,
    OnomaMatcher,
    VariantTagger,
    CitationTagger,
    replace_outside_del_tags,
    slugify_lemma,
)


def test_replace_outside_del_tags_avoids_deleted_text():
    """Text inside <del>...</del> must never be modified by entity replacers."""
    html_input = (
        'And king <del class="diff-1830">Benjamin</del> '
        '<ins class="diff-modern">Mosiah</ins> gave a gift unto Nephi.'
    )
    pattern = re.compile(r"\b(Benjamin|Mosiah|Nephi)\b")

    def dummy_repl(m):
        name = m.group(1)
        return f'<a href="#{name}">{name}*</a>'

    result = replace_outside_del_tags(html_input, pattern, dummy_repl)

    # Benjamin in <del> must be untouched
    assert '<del class="diff-1830">Benjamin</del>' in result
    # Mosiah in <ins> must be tagged
    assert '<ins class="diff-modern"><a href="#Mosiah">Mosiah*</a></ins>' in result
    # Nephi outside tags must be tagged
    assert '<a href="#Nephi">Nephi*</a>' in result


def test_replace_outside_del_tags_preserves_existing_html():
    """Existing tags must not be mangled by entity regex matching."""
    html_input = '<p>He went to <a href="#place" id="p1">Jerusalem</a> and saw Lehi.</p>'
    pattern = re.compile(r"\b(Jerusalem|Lehi)\b")

    def dummy_repl(m):
        name = m.group(1)
        return f'<span class="name">{name}</span>'

    result = replace_outside_del_tags(html_input, pattern, dummy_repl)
    # The existing <a> tag should remain intact
    assert '<a href="#place" id="p1">' in result
    assert '<span class="name">Lehi</span>' in result


def test_mosiah_21_28_pipeline_tagging():
    """Test full integration on Mosiah 21:28: Benjamin in <del> is untagged, Mosiah in <ins> is tagged."""
    onoma_dict = {
        "BENJAMIN": OnomaEntry(lemma="BENJAMIN", raw_title="BENJAMIN", definition="Son of the right hand"),
        "MOSIAH": OnomaEntry(lemma="MOSIAH", raw_title="MOSIAH", definition="Savior / Deliverer"),
        "LIMHI": OnomaEntry(lemma="LIMHI", raw_title="LIMHI", definition="King"),
        "AMMON": OnomaEntry(lemma="AMMON", raw_title="AMMON", definition="People"),
    }
    bom_1830 = {
        "mosiah-21-28": (
            "And now Limhi was again filled with joy on learning from the mouth of Ammon "
            "that king Benjamin had a gift from God, whereby he could interpret such engravings; "
            "yea, and Ammon also did rejoice."
        )
    }

    ch = Chapter(
        book_slug="mosiah",
        book_title="The Book of Mosiah",
        chapter_num=21,
        chapter_key="mosiah-21",
        verses=[
            Verse(
                verse_key="mosiah-21-28",
                book_slug="mosiah",
                chapter_num=21,
                verse_num=28,
                text=(
                    "And now Limhi was again filled with joy on learning from the mouth of Ammon "
                    "that king Mosiah had a gift from God, whereby he could interpret such engravings; "
                    "yea, and Ammon also did rejoice."
                ),
            )
        ],
    )

    # 1. Revision tagger
    rev_tagger = RevisionTagger(bom_1830)
    rev_count = rev_tagger.tag_chapter_revisions(ch)
    assert rev_count == 1

    # 2. Onoma matcher
    matcher = OnomaMatcher(onoma_dict)
    ch_onoma, o_count = matcher.tag_chapter_verses(ch)

    # 3. Textual variant tagger
    var_dict = {
        "mosiah-21-28": [
            TextualVariant(
                verse_key="mosiah-21-28",
                target_phrase="king Benjamin vs king Mosiah",
                reading_1830="king Benjamin",
                reading_modern="king Mosiah",
                explanation="Chronological harmonization",
                source="Critical Text Project",
            )
        ]
    }
    var_tagger = VariantTagger(var_dict)
    v_count = var_tagger.tag_chapter_variants(ch)
    assert v_count == 1

    # 4. Citation tagger
    cit_dict = {
        "mosiah-21-28": [
            Citation(
                speaker="Brigham Young",
                source="Journal of Discourses",
                citation="JD 11:120",
                year=1865,
                excerpt="Remarkable discourse on interpreters.",
            )
        ]
    }
    cit_tagger = CitationTagger(cit_dict)
    c_count = cit_tagger.tag_chapter_citations(ch)
    assert c_count == 1

    v = ch.verses[0]
    # Check that Benjamin is in <del> and has no footnote
    assert '<del class="diff-1830">Benjamin</del>' in v.tagged_html
    # Check that Mosiah is in <ins> and has onoma footnote
    assert '<ins class="diff-modern">Mosiah<a epub:type="noteref" class="noteref onoma-ref" href="#fn-onoma-mosiah" id="ref-onoma-mosiah"><sup>*</sup></a></ins>' in v.tagged_html
    # Check variant link
    assert 'href="#fn-var-mosiah-21-28"' in v.tagged_html
    # Check citation link
    assert 'href="#fn-cit-mosiah-21-28"' in v.tagged_html

    # Check XML well-formedness with epub namespace
    xml_doc = (
        f'<p xmlns="http://www.w3.org/1999/xhtml" '
        f'xmlns:epub="http://www.idpf.org/2007/ops">{v.tagged_html}</p>'
    )
    ET.fromstring(xml_doc)
