# Beautiful Feet: Book of Mormon Early-Source & Onomasticon Study EPUB

A comprehensive, standalone EPUB3 scholarly edition of the Book of Mormon optimized for Kindle e-readers and modern digital reading devices.

This edition features in-place lexical etymologies from the *Book of Mormon Onomasticon*, 31 landmark textual variants from the 1830 First Edition and printer's manuscripts, 9,764 verbatim 19th-century discourse excerpts from the *BYU Scripture Citation Index*, and three extensive scholarly appendices.

---

## Key Features

1. **Onomasticon Etymology Notes (Blue `*` Markers):**
   - In-place lexical footnotes on proper names, peoples, and geographical terms (376 canonical lemmas).
   - Includes canonical lemma, Deseret Alphabet phonetic spelling (e.g., `𐐢𐐨𐐸𐐪𐐨`, `𐐤𐐨𐑁𐐪𐐨`), IPA pronunciation, historical classification (e.g., Lehite PN, Nephite GN, Jaredite title), definition, and Semitic / Egyptian root derivations.
   - Distinct entities are tagged on their first occurrence in each chapter to preserve narrative reading flow.

2. **Landmark Textual Variants (Amber `[v]` Markers):**
   - 31 landmark textual and doctrinal variants documenting the evolution of the text between the 1830 first edition, Oliver Cowdery's printer's manuscript, the Original Manuscript, and the modern text.
   - Grounded in Royal Skousen's *Book of Mormon Critical Text Project*, highlighting key Christological clarifications, compositor corrections, and ancient poetic parallelism (such as the Hebrew/Septuagint colometry in 2 Nephi 12:16).

3. **Verbatim 19th-Century Discourse Excerpts (Crimson `[n]` Markers):**
   - Rather than bare scripture references, each citation features the **verbatim 1–3 paragraph historical discourse excerpt** where early Church leaders expounded that exact verse.
   - Over 9,760 excerpts strictly from foundational 19th-century sources (1830–1900):
     - *Journal of Discourses* (JD 1–26, 1854–1886)
     - *Teachings of the Prophet Joseph Smith* (TPJS)
     - *History of the Church* (HC)
     - Early periodicals (*Times and Seasons*, *Millennial Star*)
   - Post-1900 General Conference addresses are excluded to maintain a sharp historical focus on foundational restoration discourses.

4. **Scholarly Back-Matter (Appendices):**
   - **Appendix A: Historical Speaker & Source Index:** Comprehensive biographical register of all 19th-century speakers (Joseph Smith, Brigham Young, John Taylor, Orson Pratt, Wilford Woodruff, etc.), their ministry dates, total citations, and an exhaustive scriptural index of every verse they expounded.
   - **Appendix B: Complete Onomasticon Lexicon & Name Gazetteer:** Full A-to-Z scholarly dictionary of all 376 Book of Mormon lemmas, with Deseret Alphabet typography, IPA pronunciation, classification, and etymological summaries.
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
- **Onomasticon Annotations:** 1,999 in-place lexical markers (`*`).
- **Landmark Textual Variants:** 31 landmark verses annotated with manuscript/1830 comparative readings (`[v]`).
- **19th-Century Citation Footnotes:** 2,488 verse-end citations (`[n]`).
- **Verbatim Discourse Blockquotes:** 9,764 formatted historical sermon excerpts.
- **Internal Anchors:** 4,518 bidirectional footnote references with 100% resolution (0 broken links).
- **Output File Size:** 6.32 MB standalone EPUB3 publication.
