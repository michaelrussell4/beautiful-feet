"""Parser for Book of Mormon Markdown raw text."""

from __future__ import annotations
import re
import os
from typing import List, Dict, Tuple
from .models import Book, Chapter, Verse

BOOK_METADATA: Dict[str, Tuple[int, str, str]] = {
    "1 Nephi": (205, "1-ne", "First Book of Nephi"),
    "2 Nephi": (206, "2-ne", "Second Book of Nephi"),
    "Jacob": (207, "jacob", "The Book of Jacob"),
    "Enos": (208, "enos", "The Book of Enos"),
    "Jarom": (209, "jarom", "The Book of Jarom"),
    "Omni": (210, "omni", "The Book of Omni"),
    "Words of Mormon": (211, "w-of-m", "The Words of Mormon"),
    "Mosiah": (212, "mosiah", "The Book of Mosiah"),
    "Alma": (213, "alma", "The Book of Alma"),
    "Helaman": (214, "hel", "The Book of Helaman"),
    "3 Nephi": (215, "3-ne", "Third Book of Nephi"),
    "4 Nephi": (216, "4-ne", "Fourth Book of Nephi"),
    "Mormon": (217, "morm", "The Book of Mormon"),
    "Ether": (218, "ether", "The Book of Ether"),
    "Moroni": (219, "moroni", "The Book of Moroni"),
}


def normalize_title(title: str) -> str:
    """Normalize non-breaking spaces and extra whitespace in headings."""
    cleaned = title.replace("\xa0", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def parse_book_of_mormon_md(md_path: str = "assets/raw/Book of Mormon.md") -> List[Book]:
    """Parse the raw Book of Mormon markdown file into structured Book, Chapter, and Verse objects."""
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Source markdown file not found: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()

    books: List[Book] = []
    current_book: Book | None = None
    current_chapter: Chapter | None = None

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        # Level 2 Heading: ## Book Name
        m_book = re.match(r"^##\s+(.+)$", line_str)
        if m_book:
            raw_name = normalize_title(m_book.group(1))
            meta = BOOK_METADATA.get(raw_name)
            if not meta:
                # Try finding match ignoring case
                for k, v in BOOK_METADATA.items():
                    if k.lower() == raw_name.lower():
                        meta = v
                        break
            if not meta:
                raise ValueError(f"Unknown book heading in markdown: {raw_name}")

            book_id, slug, full_title = meta
            current_book = Book(book_id=book_id, slug=slug, title=full_title)
            books.append(current_book)
            current_chapter = None
            continue

        # Level 3 Heading: ### Book Chapter
        m_ch = re.match(r"^###\s+(.+)$", line_str)
        if m_ch:
            raw_ch = normalize_title(m_ch.group(1))
            # Extract chapter number at the end
            m_num = re.search(r"(\d+)$", raw_ch)
            if not m_num:
                raise ValueError(f"Could not parse chapter number from: {raw_ch}")
            ch_num = int(m_num.group(1))

            if current_book is None:
                raise ValueError(f"Chapter found without book: {raw_ch}")

            ch_key = f"{current_book.slug}-{ch_num}"
            current_chapter = Chapter(
                book_slug=current_book.slug,
                book_title=current_book.title,
                chapter_num=ch_num,
                chapter_key=ch_key,
            )
            current_book.chapters.append(current_chapter)
            continue

        # Verse line: <sup>1</sup> Verse text...
        m_verse = re.match(r"^<sup>(\d+)</sup>\s*(.+)$", line_str)
        if m_verse:
            if current_chapter is None or current_book is None:
                continue  # skip any preamble
            v_num = int(m_verse.group(1))
            v_text = m_verse.group(2).strip()
            v_key = f"{current_book.slug}-{current_chapter.chapter_num}-{v_num}"

            verse = Verse(
                book_slug=current_book.slug,
                chapter_num=current_chapter.chapter_num,
                verse_num=v_num,
                verse_key=v_key,
                text=v_text,
            )
            current_chapter.verses.append(verse)

    # Sort books in canonical scripture order (205 through 219)
    books.sort(key=lambda b: b.book_id)
    for b in books:
        b.chapters.sort(key=lambda c: c.chapter_num)
        for c in b.chapters:
            c.verses.sort(key=lambda v: v.verse_num)

    return books
