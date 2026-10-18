"""Unit tests for EPUB rendering, stylesheets, and XHTML generation."""

import xml.etree.ElementTree as ET
import pytest

from beautiful_feet.models import Chapter, Verse
from beautiful_feet.builder import (
    CSS_CONTENT,
    render_chapter_xhtml,
    render_title_page_xhtml,
    render_intro_xhtml,
)


def test_css_contains_diff_styles():
    """Verify CSS stylesheet defines 1830 revision styles for light and dark modes."""
    # Light mode
    assert "del.diff-1830" in CSS_CONTENT
    assert "ins.diff-modern" in CSS_CONTENT
    assert "text-decoration: line-through" in CSS_CONTENT

    # Dark mode media query
    assert "@media (prefers-color-scheme: dark)" in CSS_CONTENT
    dark_section = CSS_CONTENT.split("@media (prefers-color-scheme: dark)")[1]
    assert "del.diff-1830" in dark_section
    assert "ins.diff-modern" in dark_section


def test_render_chapter_xhtml_validity():
    """Verify render_chapter_xhtml produces strict, well-formed XHTML."""
    ch = Chapter(
        book_slug="1-ne",
        book_title="First Book of Nephi",
        chapter_num=1,
        chapter_key="1-ne-1",
        verses=[
            Verse(
                verse_key="1-ne-1-1",
                book_slug="1-ne",
                chapter_num=1,
                verse_num=1,
                text="I, Nephi, having been born of goodly parents...",
                tagged_html="I, Nephi, having been born of goodly parents...",
            ),
            Verse(
                verse_key="1-ne-1-2",
                book_slug="1-ne",
                chapter_num=1,
                verse_num=2,
                text="Yea, I make a record...",
                tagged_html='Yea, I make a record in the language of my father <del class="diff-1830">which</del> <ins class="diff-modern">whom</ins> I honor.',
            ),
        ],
    )

    xhtml = render_chapter_xhtml(ch)
    assert 'xmlns="http://www.w3.org/1999/xhtml"' in xhtml
    assert 'xmlns:epub="http://www.idpf.org/2007/ops"' in xhtml
    assert 'id="v1"' in xhtml
    assert 'id="v2"' in xhtml

    # Parse and validate with XML parser
    root = ET.fromstring(xhtml)
    assert root.tag.endswith("html")


def test_render_title_page_xhtml_validity():
    """Verify title page produces valid XML."""
    title_xhtml = render_title_page_xhtml()
    root = ET.fromstring(title_xhtml)
    assert root.tag.endswith("html")


def test_render_intro_xhtml_validity():
    """Verify Reader's Guide produces valid XML."""
    intro_xhtml = render_intro_xhtml()
    root = ET.fromstring(intro_xhtml)
    assert root.tag.endswith("html")
    assert "Inline 1830 First Edition Revisions" in intro_xhtml


def test_render_chapter_footnotes_layout_and_titles():
    """Verify footnotes have no top return link, have bottom return link, and start with explanatory titles."""
    from beautiful_feet.models import OnomaEntry, Citation
    ch = Chapter(
        book_slug="1-ne",
        book_title="First Book of Nephi",
        chapter_num=1,
        chapter_key="1-ne-1",
        verses=[
            Verse(
                verse_key="1-ne-1-1",
                book_slug="1-ne",
                chapter_num=1,
                verse_num=1,
                text="I, Nephi...",
                tagged_html="I, Nephi...",
            )
        ],
        onoma_entries={
            "nephi": OnomaEntry(
                lemma="Nephi",
                raw_title="NEPHI",
                classification="Lehite PN, Lehite GN, Lehite Gentilic, Lehite Title",
                pronunciation="niːfaɪ",
                etymology_paragraphs=[
                    "First paragraph of etymology proposal.",
                    "Second paragraph with Egyptian nfr.",
                    "Third paragraph discussing West Semitic roots.",
                ],
            )
        },
        citation_map={
            "1-ne-1-1": [
                Citation(
                    speaker="Brigham Young",
                    source="Journal of Discourses",
                    citation="JD 1:123",
                    year=1853,
                    excerpt="Excerpt text on verse 1.",
                )
            ]
        },
    )

    xhtml = render_chapter_xhtml(ch)

    # 1. Verify XML validity
    root = ET.fromstring(xhtml)
    assert root.tag.endswith("html")

    # 2. Verify NO top return links
    assert "fn-nav-top" not in xhtml

    # 3. Verify bottom return links exist
    assert "fn-nav-bottom" in xhtml
    assert 'class="return-link" title="Return to verse 1">Return to verse 1 &#8617;</a>' in xhtml

    # 4. Verify onomasticon title and body paragraphs
    assert '<p class="onoma-title">Name Meaning of Nephi</p>' in xhtml
    assert '<span class="onoma-class">Lehite PN, Lehite GN, Lehite Gentilic, Lehite Title</span>' in xhtml
    assert '<p class="onoma-p">First paragraph of etymology proposal.</p>' in xhtml
    assert '<p class="onoma-p">Second paragraph with Egyptian nfr.</p>' in xhtml
    assert '<p class="onoma-p">Third paragraph discussing West Semitic roots.</p>' in xhtml

    # 5. Verify citation header
    assert '<p class="cit-header">Early Historical Discourses on Verse 1:</p>' in xhtml


def test_render_onomasticon_appendix_paragraphs():
    """Verify Appendix B renders all etymology paragraphs as separate paragraphs."""
    from beautiful_feet.models import OnomaEntry
    from beautiful_feet.appendices import render_onoma_gazetteer_xhtml

    entries = {
        "NEPHI": OnomaEntry(
            lemma="Nephi",
            raw_title="NEPHI",
            classification="Lehite PN, Lehite GN",
            pronunciation="niːfaɪ",
            etymology_paragraphs=[
                "First proposal paragraph.",
                "Second proposal paragraph.",
            ],
        )
    }
    appendix_xhtml = render_onoma_gazetteer_xhtml(entries)
    # Validate with ET after substituting XHTML named entities
    valid_xml = appendix_xhtml.replace("&bull;", "&#8226;")
    root = ET.fromstring(valid_xml)
    assert root.tag.endswith("html")

    assert "First proposal paragraph." in appendix_xhtml
    assert "Second proposal paragraph." in appendix_xhtml
    assert '<span class="onoma-class"' in appendix_xhtml
    assert "Lehite PN, Lehite GN" in appendix_xhtml
