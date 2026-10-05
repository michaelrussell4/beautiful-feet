"""Data models for Book of Mormon Early-Source & Onomasticon Study EPUB."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Citation:
    speaker: str
    source: str
    citation: str
    year: Optional[int] = None
    talk_title: str = ""
    talk_id: str = ""
    target_id: str = ""
    excerpt: str = ""

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "source": self.source,
            "citation": self.citation,
            "year": self.year,
            "talk_title": self.talk_title,
            "talk_id": self.talk_id,
            "target_id": self.target_id,
            "excerpt": self.excerpt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Citation:
        return cls(
            speaker=data.get("speaker", ""),
            source=data.get("source", ""),
            citation=data.get("citation", ""),
            year=data.get("year"),
            talk_title=data.get("talk_title", ""),
            talk_id=data.get("talk_id", ""),
            target_id=data.get("target_id", ""),
            excerpt=data.get("excerpt", ""),
        )


@dataclass
class OnomaEntry:
    lemma: str
    raw_title: str
    classification: str = ""
    definition: str = ""
    deseret: str = ""
    pronunciation: str = ""
    summary: str = ""
    etymology_paragraphs: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lemma": self.lemma,
            "raw_title": self.raw_title,
            "classification": self.classification,
            "definition": self.definition,
            "deseret": self.deseret,
            "pronunciation": self.pronunciation,
            "summary": self.summary,
            "etymology_paragraphs": self.etymology_paragraphs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OnomaEntry:
        return cls(
            lemma=data.get("lemma", ""),
            raw_title=data.get("raw_title", ""),
            classification=data.get("classification", ""),
            definition=data.get("definition", ""),
            deseret=data.get("deseret", ""),
            pronunciation=data.get("pronunciation", ""),
            summary=data.get("summary", ""),
            etymology_paragraphs=data.get("etymology_paragraphs", []),
        )


@dataclass
class TextualVariant:
    verse_key: str
    target_phrase: str
    reading_1830: str
    reading_modern: str
    explanation: str
    source: str = "1830 First Edition / Critical Text"

    def to_dict(self) -> dict:
        return {
            "verse_key": self.verse_key,
            "target_phrase": self.target_phrase,
            "reading_1830": self.reading_1830,
            "reading_modern": self.reading_modern,
            "explanation": self.explanation,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TextualVariant:
        return cls(
            verse_key=data.get("verse_key", ""),
            target_phrase=data.get("target_phrase", ""),
            reading_1830=data.get("reading_1830", ""),
            reading_modern=data.get("reading_modern", ""),
            explanation=data.get("explanation", ""),
            source=data.get("source", "1830 First Edition / Critical Text"),
        )


@dataclass
class Verse:
    book_slug: str
    chapter_num: int
    verse_num: int
    verse_key: str  # e.g., "1-ne-1-4"
    text: str
    tagged_html: str = ""
    onoma_lemmas: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    variants: List[TextualVariant] = field(default_factory=list)


@dataclass
class Chapter:
    book_slug: str
    book_title: str
    chapter_num: int
    chapter_key: str  # e.g., "1-ne-1"
    verses: List[Verse] = field(default_factory=list)
    onoma_entries: Dict[str, OnomaEntry] = field(default_factory=dict)
    citation_map: Dict[str, List[Citation]] = field(default_factory=dict)
    variant_map: Dict[str, List[TextualVariant]] = field(default_factory=dict)


@dataclass
class Book:
    book_id: int
    slug: str
    title: str
    chapters: List[Chapter] = field(default_factory=list)
