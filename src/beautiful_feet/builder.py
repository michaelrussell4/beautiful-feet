"""EPUB3 generator for the Book of Mormon Early-Source & Onomasticon Study Edition."""

from __future__ import annotations
import os
import re
import html
import uuid
from typing import List, Dict, Optional
import ebooklib
from ebooklib import epub

from .models import Book, Chapter, Verse, OnomaEntry, Citation, TextualVariant
from .tagger import slugify_lemma
from .appendices import (
    render_speaker_index_xhtml,
    render_onoma_gazetteer_xhtml,
    render_chronology_xhtml,
)


CSS_CONTENT = """/* Book of Mormon Early-Source & Onomasticon Study Edition Stylesheet */

@charset "utf-8";

/* Base Typography & Page Flow */
body {
    font-family: Bookerly, "Amazon Ember", Georgia, "Palatino Linotype", "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.55;
    margin: 5% 5% 5% 5%;
    text-align: justify;
    text-justify: inter-word;
    -webkit-hyphens: auto;
    -moz-hyphens: auto;
    hyphens: auto;
    color: #1a1a1a;
    background-color: #faf9f6;
}

/* Headings */
h1.title-main {
    font-family: "Cinzel", "Trajan Pro", Georgia, serif;
    font-size: 2.2em;
    text-align: center;
    margin-top: 1.8em;
    margin-bottom: 0.3em;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #2b2b2b;
    font-weight: bold;
}

h2.title-sub {
    font-family: "Cinzel", "Trajan Pro", Georgia, serif;
    font-size: 1.25em;
    text-align: center;
    margin-top: 0.2em;
    margin-bottom: 1.2em;
    letter-spacing: 0.04em;
    font-weight: normal;
    color: #555555;
    font-style: italic;
}

h1.book-title {
    font-family: "Cinzel", "Trajan Pro", Georgia, serif;
    font-size: 1.7em;
    text-align: center;
    margin-top: 1.2em;
    margin-bottom: 0.2em;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #222222;
    border-bottom: 2px solid #8c6d3b;
    padding-bottom: 0.3em;
}

h2.chapter-title {
    font-family: "Cinzel", "Trajan Pro", Georgia, serif;
    font-size: 1.25em;
    text-align: center;
    margin-top: 0.8em;
    margin-bottom: 1.4em;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #5c4b37;
    font-weight: 600;
}

h3.footnotes-title {
    font-family: "Cinzel", "Trajan Pro", Georgia, serif;
    font-size: 1.1em;
    text-align: left;
    margin-top: 1em;
    margin-bottom: 0.8em;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #4a3c2c;
    border-bottom: 1px solid #d4c5b2;
    padding-bottom: 0.2em;
}

/* Verses */
p.verse {
    margin: 0 0 0.65em 0;
    text-indent: 0;
    line-height: 1.55;
    position: relative;
}

span.verse-num {
    font-family: Bookerly, "Amazon Ember", sans-serif;
    font-size: 0.78em;
    font-weight: bold;
    color: #8c6d3b;
    margin-right: 0.35em;
    vertical-align: 0.25em;
    line-height: 1;
}

/* Noteref Footnote Links */
a.noteref {
    text-decoration: none;
    font-weight: bold;
    line-height: 1;
}

a.onoma-ref {
    color: #0b5394;
    padding: 0 0.1em;
}

a.onoma-ref sup {
    font-size: 0.8em;
    vertical-align: 0.35em;
}

a.cit-ref {
    color: #990000;
    margin-left: 0.15em;
}

a.cit-ref sup {
    font-size: 0.72em;
    vertical-align: 0.35em;
    font-weight: 600;
}

a.var-ref {
    color: #b8860b;
    margin-left: 0.15em;
}

a.var-ref sup {
    font-size: 0.72em;
    vertical-align: 0.35em;
    font-weight: bold;
}

/* Footnotes Section & Aside Items */
section.footnotes-section {
    margin-top: 2.8em;
    padding-top: 1em;
    border-top: 2px solid #e0d8cc;
}

aside.footnote-item {
    margin-bottom: 1.4em;
    padding: 0.7em 0.9em;
    background-color: #f7f5f0;
    border-left: 3.5px solid #8c6d3b;
    border-radius: 2px;
    font-size: 0.9em;
    line-height: 1.5;
}

aside.onoma-footnote {
    border-left-color: #0b5394;
    background-color: #f0f4f8;
}

aside.cit-footnote {
    border-left-color: #990000;
    background-color: #fcf4f4;
}

aside.var-footnote {
    border-left-color: #b8860b;
    background-color: #fdfaf0;
}

/* Onomasticon Entry Components */
.onoma-header {
    margin-bottom: 0.35em;
    display: block;
}

.onoma-lemma {
    font-weight: bold;
    font-size: 1.05em;
    color: #0b5394;
}

.onoma-deseret {
    font-size: 1.15em;
    margin-left: 0.4em;
    color: #222222;
    font-weight: normal;
}

.onoma-pron {
    font-style: italic;
    color: #555555;
    margin-left: 0.4em;
    font-size: 0.95em;
}

.onoma-class {
    display: inline-block;
    font-size: 0.75em;
    font-weight: 600;
    text-transform: uppercase;
    background-color: #dbe5ee;
    color: #1a446c;
    padding: 0.1em 0.45em;
    border-radius: 3px;
    margin-left: 0.5em;
    letter-spacing: 0.04em;
}

p.onoma-def {
    margin: 0.25em 0;
    font-size: 0.9em;
    color: #444444;
    font-style: italic;
}

p.onoma-summary {
    margin: 0.3em 0 0 0;
    color: #222222;
}

/* Citation Entry Components */
p.cit-header {
    font-weight: bold;
    color: #781010;
    margin: 0 0 0.5em 0;
    font-size: 0.98em;
}

.cit-discourse-item {
    margin-bottom: 1.1em;
    padding-bottom: 0.8em;
    border-bottom: 1px dashed #e8d8d8;
}

.cit-discourse-item:last-child {
    border-bottom: none;
    margin-bottom: 0.4em;
    padding-bottom: 0;
}

.cit-meta {
    margin-bottom: 0.25em;
    line-height: 1.4;
}

.cit-speaker {
    font-weight: bold;
    color: #222222;
    font-size: 1em;
}

.cit-source-pill {
    display: inline-block;
    font-size: 0.75em;
    font-weight: 600;
    background-color: #f0dede;
    color: #781010;
    padding: 0.1em 0.4em;
    border-radius: 3px;
    margin: 0 0.3em;
}

.cit-ref-details {
    color: #444444;
    font-weight: 600;
}

.cit-year {
    color: #666666;
    font-size: 0.9em;
}

.cit-title-line {
    font-style: italic;
    color: #333333;
    margin: 0.15em 0 0.4em 0;
    font-size: 0.92em;
}

/* Verbatim Discourse Blockquote */
blockquote.cit-excerpt {
    margin: 0.5em 0 0.5em 0.6em;
    padding: 0.4em 0.8em;
    background-color: #ffffff;
    border-left: 2.5px solid #d4a5a5;
    border-radius: 2px;
    color: #2a2a2a;
    font-size: 0.92em;
    line-height: 1.5;
}

blockquote.cit-excerpt p {
    margin: 0 0 0.45em 0;
    text-indent: 0;
}

blockquote.cit-excerpt p:last-child {
    margin-bottom: 0;
}

/* Textual Variant Entry Components */
.var-header {
    margin-bottom: 0.4em;
}

.var-label {
    font-weight: bold;
    color: #8c6d3b;
    text-transform: uppercase;
    font-size: 0.8em;
    letter-spacing: 0.05em;
}

.var-phrase {
    font-weight: 600;
    color: #222222;
    font-size: 1em;
}

.var-comparison {
    margin: 0.5em 0;
    display: block;
}

.var-box {
    padding: 0.4em 0.6em;
    margin-bottom: 0.4em;
    border-radius: 3px;
    font-size: 0.9em;
    line-height: 1.45;
}

.var-1830 {
    background-color: #fff9e6;
    border-left: 3px solid #d4a017;
}

.var-modern {
    background-color: #f0f7ee;
    border-left: 3px solid #5a9e52;
}

p.var-explanation {
    margin: 0.4em 0;
    color: #222222;
    font-size: 0.92em;
}

p.var-source {
    font-size: 0.82em;
    color: #666666;
    margin: 0.3em 0 0 0;
}

a.return-link {
    text-decoration: none;
    color: #0b5394;
    font-weight: bold;
    margin-left: 0.3em;
}

/* Decorative Elements */
div.ornament {
    text-align: center;
    color: #8c6d3b;
    font-size: 1.2em;
    margin: 1.2em 0;
}

/* Intro & Front Matter */
.intro-box {
    background-color: #f7f5f0;
    border: 1px solid #e2dacd;
    padding: 1.2em;
    margin: 1.5em 0;
    border-radius: 4px;
}

.intro-box h3 {
    margin-top: 0;
    color: #5c4b37;
}

/* Dark Mode / Inverted Colors for Kindle Night Mode */
@media (prefers-color-scheme: dark) {
    body {
        background-color: #121212;
        color: #e0e0e0;
    }
    h1.title-main, h1.book-title, h2.chapter-title {
        color: #e8d8c8;
    }
    h2.title-sub, h3.footnotes-title {
        color: #d0c0b0;
    }
    span.verse-num {
        color: #d4a359;
    }
    aside.footnote-item {
        background-color: #1a1a1a;
        color: #e0e0e0;
    }
    aside.onoma-footnote {
        background-color: #15222e;
    }
    aside.cit-footnote {
        background-color: #261515;
    }
    aside.var-footnote {
        background-color: #242014;
    }
    blockquote.cit-excerpt {
        background-color: #181818;
        color: #d8d8d8;
        border-left-color: #782828;
    }
    .var-1830 {
        background-color: #262215;
    }
    .var-modern {
        background-color: #162416;
    }
    a.onoma-ref, .onoma-lemma {
        color: #90caf9;
    }
    .onoma-deseret {
        color: #e0e0e0;
    }
    a.cit-ref, p.cit-header {
        color: #ef9a9a;
    }
    a.var-ref, .var-label {
        color: #ffd54f;
    }
    .onoma-class {
        background-color: #26384a;
        color: #90caf9;
    }
    .cit-source-pill {
        background-color: #441a1a;
        color: #ef9a9a;
    }
    p.onoma-summary, p.var-explanation, .cit-speaker {
        color: #dddddd;
    }
    .intro-box {
        background-color: #1e1e1e;
        border-color: #333333;
    }
}
"""


def render_chapter_xhtml(chapter: Chapter) -> str:
    """Render a Chapter object into EPUB3-compliant XHTML."""
    lines: List[str] = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!DOCTYPE html>',
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">',
        "<head>",
        f"  <title>{html.escape(chapter.book_title)} {chapter.chapter_num}</title>",
        '  <link rel="stylesheet" type="text/css" href="../styles/style.css" />',
        "</head>",
        "<body>",
        '  <section epub:type="chapter" class="chapter-content">',
        f'    <h2 class="chapter-title">{html.escape(chapter.book_title)} {chapter.chapter_num}</h2>',
    ]

    # Verses
    for v in chapter.verses:
        v_body = v.tagged_html if v.tagged_html else html.escape(v.text)
        lines.append(
            f'    <p class="verse" id="v{v.verse_num}">'
            f'<span class="verse-num">{v.verse_num}</span> '
            f"{v_body}</p>"
        )

    # Footnotes Container (if chapter has onoma entries, variants, or citations)
    has_footnotes = bool(chapter.onoma_entries or chapter.variant_map or chapter.citation_map)
    if has_footnotes:
        lines.extend([
            '    <section epub:type="footnotes" class="footnotes-section">',
            '      <h3 class="footnotes-title">Study Notes &amp; Historical Expositions</h3>',
        ])

        # 1. Onomasticon Entries for this chapter
        if chapter.onoma_entries:
            lines.append("      <!-- Onomasticon Etymology Notes -->")
            for slug, entry in sorted(chapter.onoma_entries.items()):
                fn_id = f"fn-onoma-{slug}"
                ref_id = f"ref-onoma-{slug}"
                lemma_esc = html.escape(entry.lemma)
                deseret_html = (
                    f'<span class="onoma-deseret">{html.escape(entry.deseret)}</span>'
                    if entry.deseret
                    else ""
                )
                pron_html = (
                    f'<span class="onoma-pron">/{html.escape(entry.pronunciation)}/</span>'
                    if entry.pronunciation
                    else ""
                )
                class_html = (
                    f'<span class="onoma-class">{html.escape(entry.classification)}</span>'
                    if entry.classification
                    else ""
                )
                def_html = (
                    f'<p class="onoma-def">{html.escape(entry.definition)}</p>'
                    if entry.definition
                    else ""
                )
                summary_esc = html.escape(entry.summary) if entry.summary else "No additional notes."

                lines.extend([
                    f'      <aside epub:type="footnote" id="{fn_id}" class="footnote-item onoma-footnote">',
                    '        <div class="onoma-header">',
                    f'          <span class="onoma-lemma">{lemma_esc}</span>{deseret_html}{pron_html}{class_html}',
                    "        </div>",
                    f"        {def_html}" if def_html else "",
                    f'        <p class="onoma-summary">{summary_esc}<a href="#{ref_id}" class="return-link" title="Return to text"> ↩</a></p>',
                    "      </aside>",
                ])

        # 2. Textual Variant Entries for this chapter
        if chapter.variant_map:
            lines.append("      <!-- Textual Variants -->")
            for v_key, var_list in sorted(
                chapter.variant_map.items(),
                key=lambda item: int(item[0].split("-")[-1]) if item[0].split("-")[-1].isdigit() else 0,
            ):
                fn_id = f"fn-var-{v_key}"
                ref_id = f"ref-var-{v_key}"

                for var in var_list:
                    phrase_esc = html.escape(var.target_phrase)
                    r1830_esc = html.escape(var.reading_1830)
                    rmod_esc = html.escape(var.reading_modern)
                    exp_esc = html.escape(var.explanation)
                    src_esc = html.escape(var.source)

                    lines.extend([
                        f'      <aside epub:type="footnote" id="{fn_id}" class="footnote-item var-footnote">',
                        '        <div class="var-header">',
                        f'          <span class="var-label">Textual Variant:</span> <span class="var-phrase">&ldquo;{phrase_esc}&rdquo;</span>',
                        "        </div>",
                        '        <div class="var-comparison">',
                        '          <div class="var-box var-1830">',
                        f'            <strong>1830 First Edition / Manuscript:</strong><br />&ldquo;{r1830_esc}&rdquo;',
                        "          </div>",
                        '          <div class="var-box var-modern">',
                        f'            <strong>Modern Reading:</strong><br />&ldquo;{rmod_esc}&rdquo;',
                        "          </div>",
                        "        </div>",
                        f'        <p class="var-explanation">{exp_esc}</p>',
                        f'        <p class="var-source"><em>Source:</em> {src_esc}<a href="#{ref_id}" class="return-link" title="Return to verse"> ↩</a></p>',
                        "      </aside>",
                    ])

        # 3. Early Citation Entries for this chapter
        if chapter.citation_map:
            lines.append("      <!-- Early Historical Citations & Discourse Excerpts -->")
            for v_key, cits in sorted(
                chapter.citation_map.items(),
                key=lambda item: int(item[0].split("-")[-1]) if item[0].split("-")[-1].isdigit() else 0,
            ):
                v_num_str = v_key.split("-")[-1]
                fn_id = f"fn-cit-{v_key}"
                ref_id = f"ref-cit-{v_key}"

                lines.extend([
                    f'      <aside epub:type="footnote" id="{fn_id}" class="footnote-item cit-footnote">',
                    f'        <p class="cit-header">Early Historical Discourses on Verse {v_num_str}:</p>',
                    '        <div class="cit-discourse-list">',
                ])

                for c in cits:
                    speaker_html = (
                        f'<span class="cit-speaker">{html.escape(c.speaker)}</span>'
                        if c.speaker
                        else ""
                    )
                    source_html = (
                        f'<span class="cit-source-pill">{html.escape(c.source)}</span>'
                        if c.source
                        else ""
                    )
                    cit_str_html = (
                        f'<span class="cit-ref-details">{html.escape(c.citation)}</span>'
                        if c.citation
                        else ""
                    )
                    year_html = (
                        f'<span class="cit-year">({c.year})</span>' if c.year else ""
                    )
                    title_html = (
                        f'          <p class="cit-title-line">&ldquo;{html.escape(c.talk_title)}&rdquo;</p>'
                        if c.talk_title
                        else ""
                    )

                    lines.extend([
                        '          <div class="cit-discourse-item">',
                        f'            <div class="cit-meta">{speaker_html} &bull; {source_html} {cit_str_html} {year_html}</div>',
                        f"{title_html}" if title_html else "",
                    ])

                    if c.excerpt:
                        paras = c.excerpt.split("\n\n")
                        lines.append('            <blockquote class="cit-excerpt">')
                        for p in paras:
                            if p.strip():
                                lines.append(f"              <p>{html.escape(p.strip())}</p>")
                        lines.append("            </blockquote>")

                    lines.append("          </div>")

                lines.extend([
                    "        </div>",
                    f'        <p style="margin-top: 0.6em;"><a href="#{ref_id}" class="return-link">Return to verse {v_num_str} ↩</a></p>',
                    "      </aside>",
                ])

        lines.append("    </section>")

    lines.extend([
        "  </section>",
        "</body>",
        "</html>",
    ])

    return "\n".join([line for line in lines if line])


def render_title_page_xhtml() -> str:
    """Render elegant title page XHTML."""
    return """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head>
  <title>Title Page</title>
  <link rel="stylesheet" type="text/css" href="../styles/style.css" />
</head>
<body>
  <section epub:type="titlepage" class="titlepage-section">
    <div style="text-align: center; margin-top: 2.5em; margin-bottom: 2em;">
      <h1 class="title-main">The Book of Mormon</h1>
      <h2 class="title-sub">Early-Source &amp; Onomasticon Study Edition</h2>
      
      <div class="ornament">&#10087; &bull; &#10086; &bull; &#10087;</div>
      
      <p style="font-size: 1.1em; color: #444; margin-top: 1.5em; font-style: italic;">
        An Account Written by the Hand of Mormon<br />
        upon Plates Taken from the Plates of Nephi
      </p>
      
      <p style="font-size: 0.95em; color: #666; margin-top: 2.5em;">
        Translated by Joseph Smith, Jun.
      </p>
      
      <div style="margin-top: 3.5em; padding-top: 1.5em; border-top: 1px solid #dcd3c5; font-size: 0.88em; color: #777;">
        <p>Featuring in-place lexical etymologies from the <em>Book of Mormon Onomasticon</em>,<br />
        verbatim historical discourse excerpts from the <em>BYU Scripture Citation Index</em> (1830&ndash;1900),<br />
        and textual variants from the 1830 First Edition &amp; Manuscripts.</p>
        <p style="margin-top: 1em;">Beautiful Feet Press &bull; Scholarly Study Series</p>
      </div>
    </div>
  </section>
</body>
</html>"""


def render_intro_xhtml() -> str:
    """Render Introduction and Reader's Guide XHTML."""
    return """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head>
  <title>Reader's Guide</title>
  <link rel="stylesheet" type="text/css" href="../styles/style.css" />
</head>
<body>
  <section epub:type="frontmatter" class="intro-section">
    <h1 class="book-title">Reader&rsquo;s Guide</h1>
    <div class="ornament">&#10087; &bull; &#10086; &bull; &#10087;</div>
    
    <div class="intro-box">
      <h3>About this Scholarly Study Edition</h3>
      <p>This edition integrates three primary research dimensions directly into the sacred text of the Book of Mormon, formatted specifically for Kindle e-readers and modern digital devices:</p>
      <ol>
        <li>
          <strong>Book of Mormon Onomasticon:</strong> Proper names and geographical designations are tagged on their initial occurrence in each chapter with a blue asterisk (<span style="color:#0b5394; font-weight:bold;">*</span>). Tapping opens a modal note providing the canonical lemma, Deseret Alphabet phonetic spelling, IPA pronunciation, historical classification, definition, and synthesized Semitic / Egyptian etymological roots.
        </li>
        <li>
          <strong>Textual Variants (1830 First Edition &amp; Manuscripts):</strong> Significant historical and doctrinal variants are marked with an amber badge (<span style="color:#b8860b; font-weight:bold;">[v]</span>). These display a direct comparative analysis between the 1830 typesetting, Oliver Cowdery&rsquo;s manuscripts, and the modern text, grounded in Royal Skousen&rsquo;s <em>Book of Mormon Critical Text Project</em>.
        </li>
        <li>
          <strong>19th-Century Historical Discourse Excerpts (1830&ndash;1900):</strong> Verses expounded by early Church leaders are marked with crimson numbered citations (<span style="color:#990000; font-weight:bold;">[1]</span>). Unlike traditional bare cross-references, each footnote features the <em>verbatim 1&ndash;3 paragraph discourse excerpt</em> from the <em>Journal of Discourses</em> (1854&ndash;1886) or <em>Teachings of the Prophet Joseph Smith</em> (TPJS). Readers can read the exact theological commentary delivered by Joseph Smith, Brigham Young, John Taylor, Orson Pratt, and Wilford Woodruff on that specific passage.
        </li>
      </ol>
    </div>

    <h3 class="footnotes-title">Scholarly Back-Matter (Appendices)</h3>
    <ul class="cit-list" style="line-height: 1.6;">
      <li><strong>Appendix A: Historical Speaker &amp; Source Index:</strong> Biographical register and comprehensive scriptural citation catalog of all early Church leaders cited across the volume.</li>
      <li><strong>Appendix B: Complete Onomasticon Lexicon &amp; Name Gazetteer:</strong> Complete A&ndash;Z dictionary of all 376 proper names and geographical terms in the Nephite and Jaredite records.</li>
      <li><strong>Appendix C: Chronology, Plates &amp; Translation Overview:</strong> Master timeline from the Tower of Babel to Moroni, diagram of the plate archives, and the 1829 translation history.</li>
    </ul>

    <h3 class="footnotes-title">Kindle &amp; E-Reader Navigation</h3>
    <p>On modern Kindle devices (Paperwhite, Oasis, Scribe) and Kindle reading applications, tapping any footnote reference opens an instant pop-up reading panel without navigating away from the verse. On older e-ink devices, tapping the return symbol (<span style="color:#0b5394; font-weight:bold;">&#8617;</span>) immediately restores your exact reading position.</p>
  </section>
</body>
</html>"""


def build_study_epub(
    books: List[Book],
    onoma_data: Optional[Dict[str, OnomaEntry]] = None,
    cit_data: Optional[Dict[str, List[Citation]]] = None,
    cover_path: str = "assets/images/cover.jpg",
    output_path: str = "output/Book_of_Mormon_Early_Sources_Study_Edition.epub",
) -> str:
    """Compile all Book, Chapter, Footnote, and Appendix objects into an EPUB3 file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    book = epub.EpubBook()
    book_id = f"urn:uuid:{uuid.uuid4()}"
    book.set_identifier(book_id)
    book.set_title("The Book of Mormon: Early-Source & Onomasticon Study Edition")
    book.set_language("en")
    book.add_author("Translated by Joseph Smith, Jun.")
    book.add_metadata(
        "DC",
        "description",
        "A scholarly study edition of the Book of Mormon featuring in-place lexical etymologies from the Book of Mormon Onomasticon, 19th-century verbatim discourse excerpts from the BYU Scripture Citation Index, and textual variants from the 1830 First Edition & Manuscripts.",
    )
    book.add_metadata("DC", "publisher", "Beautiful Feet Press")

    # 1. Add Cover Image & Cover Page (if available)
    cover_item = None
    if os.path.exists(cover_path):
        with open(cover_path, "rb") as f:
            cover_bytes = f.read()
        book.set_cover("images/cover.jpg", cover_bytes, create_page=True)
        # Find and format the generated cover.xhtml for full-bleed display
        for item in book.get_items():
            if item.get_name() == "cover.xhtml":
                cover_item = item
                cover_html_custom = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head>
  <title>Cover</title>
  <style type="text/css">
    @page {{ margin: 0; padding: 0; }}
    body {{ margin: 0; padding: 0; text-align: center; background-color: #0b172a; }}
    div.cover-wrapper {{ height: 100vh; margin: 0; padding: 0; text-align: center; display: flex; justify-content: center; align-items: center; }}
    img.cover-image {{ max-height: 100%; max-width: 100%; height: 100vh; object-fit: contain; margin: 0 auto; }}
  </style>
</head>
<body>
  <div class="cover-wrapper">
    <img class="cover-image" src="images/cover.jpg" alt="The Book of Mormon: Early-Source &amp; Onomasticon Study Edition" />
  </div>
</body>
</html>"""
                cover_item.content = cover_html_custom.encode("utf-8")
                break

    # 2. Add Stylesheet
    style_item = epub.EpubItem(
        uid="style_css",
        file_name="styles/style.css",
        media_type="text/css",
        content=CSS_CONTENT.encode("utf-8"),
    )
    book.add_item(style_item)

    # 3. Add Title Page
    title_html = render_title_page_xhtml()
    title_item = epub.EpubHtml(
        title="Title Page",
        file_name="text/titlepage.xhtml",
        lang="en",
        content=title_html.encode("utf-8"),
    )
    title_item.add_item(style_item)
    book.add_item(title_item)

    # 4. Add Intro Page
    intro_html = render_intro_xhtml()
    intro_item = epub.EpubHtml(
        title="Reader's Guide",
        file_name="text/intro.xhtml",
        lang="en",
        content=intro_html.encode("utf-8"),
    )
    intro_item.add_item(style_item)
    book.add_item(intro_item)

    # 5. Add Chapters
    spine_items = ["nav"]
    toc_structure = []

    if cover_item:
        spine_items.append(cover_item)
        toc_structure.append(cover_item)

    spine_items.extend([title_item, intro_item])
    toc_structure.extend([title_item, intro_item])

    for b in books:
        book_toc_subitems = []
        for ch in b.chapters:
            file_name = f"text/{b.slug}_{ch.chapter_num:02d}.xhtml"
            ch_html = render_chapter_xhtml(ch)

            ch_item = epub.EpubHtml(
                title=f"{b.title} {ch.chapter_num}",
                file_name=file_name,
                lang="en",
                content=ch_html.encode("utf-8"),
            )
            ch_item.add_item(style_item)
            book.add_item(ch_item)

            spine_items.append(ch_item)
            book_toc_subitems.append(ch_item)

        # Add hierarchical TOC node: Book -> Chapters
        toc_structure.append((epub.Section(b.title), book_toc_subitems))

    # 5. Add Scholarly Appendices
    appendix_subitems = []

    # Appendix A: Speaker Index
    if cit_data:
        speaker_html = render_speaker_index_xhtml(cit_data)
        speaker_item = epub.EpubHtml(
            title="Appendix A: Historical Speaker & Source Index",
            file_name="text/appendix_a_speakers.xhtml",
            lang="en",
            content=speaker_html.encode("utf-8"),
        )
        speaker_item.add_item(style_item)
        book.add_item(speaker_item)
        spine_items.append(speaker_item)
        appendix_subitems.append(speaker_item)

    # Appendix B: Onomasticon Lexicon
    if onoma_data:
        gazetteer_html = render_onoma_gazetteer_xhtml(onoma_data)
        gazetteer_item = epub.EpubHtml(
            title="Appendix B: Onomasticon Lexicon & Gazetteer",
            file_name="text/appendix_b_onomasticon.xhtml",
            lang="en",
            content=gazetteer_html.encode("utf-8"),
        )
        gazetteer_item.add_item(style_item)
        book.add_item(gazetteer_item)
        spine_items.append(gazetteer_item)
        appendix_subitems.append(gazetteer_item)

    # Appendix C: Chronology & Plates
    chronology_html = render_chronology_xhtml()
    chronology_item = epub.EpubHtml(
        title="Appendix C: Chronology & Plates Overview",
        file_name="text/appendix_c_chronology.xhtml",
        lang="en",
        content=chronology_html.encode("utf-8"),
    )
    chronology_item.add_item(style_item)
    book.add_item(chronology_item)
    spine_items.append(chronology_item)
    appendix_subitems.append(chronology_item)

    if appendix_subitems:
        toc_structure.append((epub.Section("Appendices & Scholarly Indices"), appendix_subitems))

    # Configure Table of Contents & Navigation
    book.toc = toc_structure
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine_items

    # Write EPUB file
    epub.write_epub(output_path, book, {"epub3_landmark": True, "epub3_pages": False})
    return output_path
