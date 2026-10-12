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
