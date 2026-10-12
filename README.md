# Beautiful Feet: Book of Mormon 1830 Textual Revisions & Early-Source Study Edition

A comprehensive, standalone EPUB3 scholarly edition of the Book of Mormon optimized for Kindle e-readers and modern digital reading devices.

This edition features inline 1830 First Edition textual revisions with strikethrough markup, in-place lexical etymologies from the *Book of Mormon Onomasticon*, 31 landmark textual variants from the 1830 First Edition and printer's manuscripts, 4,334 verbatim historical discourse excerpts from the *BYU Scripture Citation Index* (1830–1930) deduplicated to the concluding verse of each expounded passage, and three extensive scholarly appendices.

---

## Key Features

1. **Inline 1830 First Edition Revisions (Strikethrough / Insertion View):**
   - Word-level substantive changes comparing the modern authorized text directly against the Palmyra 1830 First Edition across all 6,604 verses.
   - 1830 text that was modified or deleted is shown inline in strikethrough red (`<del class="diff-1830">...</del>`), immediately accompanied by the modern authorized reading (`<ins class="diff-modern">...</ins>`).
   - Typesetter punctuation, capitalization, and minor hyphenation noise from 1830 are filtered out to keep the prose clean, legible, and focused on substantive textual development.
   - Supported with custom light and dark mode styles for Kindle Paperwhite, Oasis, Scribe, and mobile devices.

2. **Onomasticon Etymology Notes (Blue `*` Markers):**
   - In-place lexical footnotes on proper names, peoples, and geographical terms (376 canonical lemmas).
   - Includes canonical lemma, IPA pronunciation, historical classification (e.g., Lehite PN, Nephite GN, Jaredite title), definition, and Semitic / Egyptian root derivations.
   - Distinct entities are tagged on their first occurrence in each chapter to preserve narrative reading flow.

3. **Landmark Textual Variants (Amber `[v]` Markers):**
   - 31 landmark textual and doctrinal variants documenting the evolution of the text between the 1830 first edition, Oliver Cowdery's printer's manuscript, the Original Manuscript, and the modern text.
   - Grounded in Royal Skousen's *Book of Mormon Critical Text Project*, highlighting key Christological clarifications, compositor corrections, and ancient poetic parallelism (such as the Hebrew/Septuagint colometry in 2 Nephi 12:16).

4. **Verbatim Historical Discourse Excerpts (Crimson `[n]` Markers):**
   - Rather than bare scripture references, each citation features the **verbatim 1–3 paragraph historical discourse excerpt** where early Church leaders expounded that exact passage.
   - Over 4,330 distinct excerpts strictly from foundational Restoration sources (1830–1930):
     - *Journal of Discourses* (JD 1–26, 1854–1886)
     - *Teachings of the Prophet Joseph Smith* (TPJS)
     - *History of the Church* (HC)
     - Early periodicals (*Times and Seasons*, *Millennial Star*)
   - **Range Verse Deduplication:** Multi-verse citations (e.g., 1 Nephi 1:18–20) attach exclusively to the final verse in the cited passage, eliminating 5,460 redundant duplicate notes and displaying the full covered range directly in the note header and metadata badges.

5. **Scholarly Back-Matter (Appendices):**
   - **Appendix A: Historical Speaker & Source Index:** Comprehensive biographical register of all 19th-century speakers (Joseph Smith, Brigham Young, John Taylor, Orson Pratt, Wilford Woodruff, etc.), their ministry dates, total citations, and an exhaustive scriptural index of every verse they expounded.
   - **Appendix B: Complete Onomasticon Lexicon & Name Gazetteer:** Full A-to-Z scholarly dictionary of all 376 Book of Mormon lemmas, with IPA pronunciation, classification, and etymological summaries.
   - **Appendix C: Chronology, Plates & Translation Overview:** Master chronological timeline from the Tower of Babel (ca. 2200 BC) to Moroni (421 AD), a structural diagram of the Nephite metal plate collections, and the 1829 translation history.

5. **Kindle Modal UX & E-Reader Fallback:**
   - Semantic EPUB3 markup (`epub:type="noteref"` and `<aside epub:type="footnote">`) triggers Kindle's KFX pop-up modal panel on Paperwhite, Oasis, Scribe, and Kindle apps.
   - Bidirectional anchor links (`↩`) provide instant return navigation on older e-ink devices and standard EPUB readers (Calibre, Apple Books, Kobo).
   - Fully compliant with EPUB 3.2 schema and strict XML standards (100% verified with 0 broken links).

---

## Project Structure

```text
beautiful-feet/
├── assets/
│   └── raw/
│       ├── Book of Mormon.md      # Base scripture text
│       └── ...
├── data/
│   ├── onomasticon.json           # 376 parsed Onomasticon lemma entries
│   ├── early_citations.json       # 2,488 verse keys with 9,764 enriched excerpts
│   ├── textual_variants.json      # 31 landmark textual variants
│   └── talks_cache/               # Cached HTML files of 19th-century historical discourses
├── output/
│   └── Book_of_Mormon_Early_Sources_Study_Edition.epub  # Final compiled EPUB3 (6.32 MB)
├── src/
│   └── beautiful_feet/
│       ├── __init__.py
│       ├── appendices.py          # Appendices A, B, and C generator
│       ├── builder.py             # EPUB3 compiler & Kindle stylesheet
│       ├── citation_fetcher.py    # BYU Scripture Citation Index pipeline
│       ├── cli.py                 # CLI interface
│       ├── models.py              # Dataclasses (Book, Chapter, Verse, OnomaEntry, Citation, TextualVariant)
│       ├── onoma_fetcher.py       # BYU Onomasticon MediaWiki API pipeline
│       ├── tagger.py              # Regex entity matcher, variant tagger & citation injector
│       ├── text_parser.py         # Markdown scripture text parser (canonical book ordering)
│       └── textual_variants.py    # Landmark textual variants database
├── pyproject.toml
└── README.md
```

---

## Quickstart

Run with [`uv`](https://docs.astral.sh/uv/):

```bash
# Build the complete EPUB3 edition
uv run beautiful-feet build

# Validate the generated EPUB (schema & internal link integrity)
uv run beautiful-feet validate
```

### CLI Subcommands

- `uv run beautiful-feet build`: Parses text, injects annotations and variants, compiles the study edition with Appendices to `output/Book_of_Mormon_Early_Sources_Study_Edition.epub`.
- `uv run beautiful-feet validate`: Validates EPUB structure, mimetype, container, OPF manifest, XML well-formedness, and bidirectional footnote resolution across all 245 XHTML files.
- `uv run beautiful-feet fetch-onoma [--force]`: Fetches / refreshes the complete Onomasticon dataset.
- `uv run beautiful-feet fetch-citations [--force]`: Scans all 239 chapters and fetches / refreshes early 19th-century citations from the BYU Citation Index.

---

## Verified Build Statistics

- **Canonical Order:** 15 Books (1 Nephi through Moroni), 239 Chapters, 6,604 Verses.
- **Inline 1830 Revisions:** 3,586 verses with substantive word changes from the 1830 First Edition.
- **Onomasticon Annotations:** 1,999 in-place lexical markers (`*`).
- **Landmark Textual Variants:** 31 landmark verses annotated with manuscript/1830 comparative readings (`[v]`).
- **Historical Citation Footnotes:** 1,495 expounded passage citations (`[n]`) deduplicated to the concluding verse.
- **Verbatim Discourse Blockquotes:** 4,334 formatted historical sermon excerpts across 1,068 unique discourses.
- **Internal Anchors:** 3,525 bidirectional footnote references with 100% resolution (0 broken links).
- **XML Conformance:** 100% strictly valid XML across all 246 XHTML documents.
- **Output File Size:** 6.24 MB standalone EPUB3 publication.

