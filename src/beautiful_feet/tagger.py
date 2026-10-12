"""Tagger engine for entity recognition (Onomasticon) and citation injection."""

from __future__ import annotations
import re
from typing import Dict, List, Set, Tuple
from difflib import SequenceMatcher
import html
import regex

from .models import Book, Chapter, Verse, OnomaEntry, Citation, TextualVariant
from .citation_fetcher import deduplicate_citations_to_last_verse


def slugify_lemma(lemma: str) -> str:
    """Create a URL-safe lowercase slug for footnote IDs."""
    slug = lemma.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug


def generate_verse_revision(t_1830: str, t_mod: str) -> str:
    """Generate inline strikethrough/revision markup comparing the 1830 First Edition against the modern text.

    - Word-level substantive changes: differences in words are highlighted.
    - Typesetter punctuation, hyphenation, and capitalization adjustments from 1830 are ignored.
    - 1830 words that were deleted or replaced are wrapped in <del class="diff-1830">...</del>.
    - Modern words that replace or are added to 1830 are wrapped in <ins class="diff-modern">...</ins>.
    - Verses with identical words are emitted cleanly without diff markup.
    """
    word_pattern = re.compile(r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*")

    matches_1830 = list(word_pattern.finditer(t_1830))
    matches_mod = list(word_pattern.finditer(t_mod))

    norm_1830 = [m.group(0).lower() for m in matches_1830]
    norm_mod = [m.group(0).lower() for m in matches_mod]

    # If words are identical, return the modern text directly (XML-safe)
    if norm_1830 == norm_mod:
        return html.escape(t_mod, quote=False)

    sm = SequenceMatcher(None, norm_1830, norm_mod)
    opcodes = sm.get_opcodes()

    out: List[str] = []
    mod_cursor = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            if j1 < j2:
                end_pos = matches_mod[j2 - 1].end()
                out.append(html.escape(t_mod[mod_cursor:end_pos], quote=False))
                mod_cursor = end_pos

        elif tag == "replace":
            start_pos = matches_mod[j1].start()
            if mod_cursor < start_pos:
                out.append(html.escape(t_mod[mod_cursor:start_pos], quote=False))
                mod_cursor = start_pos

            del_words = html.escape(
                " ".join(matches_1830[k].group(0) for k in range(i1, i2)), quote=False
            )
            end_pos = matches_mod[j2 - 1].end()
            rep_mod_text = html.escape(t_mod[start_pos:end_pos], quote=False)

            out.append(
                f'<del class="diff-1830">{del_words}</del> <ins class="diff-modern">{rep_mod_text}</ins>'
            )
            mod_cursor = end_pos

        elif tag == "delete":
            del_words = html.escape(
                " ".join(matches_1830[k].group(0) for k in range(i1, i2)), quote=False
            )
            out.append(f'<del class="diff-1830">{del_words}</del> ')

        elif tag == "insert":
            start_pos = matches_mod[j1].start()
            if mod_cursor < start_pos:
                out.append(html.escape(t_mod[mod_cursor:start_pos], quote=False))
                mod_cursor = start_pos
            end_pos = matches_mod[j2 - 1].end()
            ins_mod_text = html.escape(t_mod[start_pos:end_pos], quote=False)
            out.append(f'<ins class="diff-modern">{ins_mod_text}</ins>')
            mod_cursor = end_pos

    if mod_cursor < len(t_mod):
        out.append(html.escape(t_mod[mod_cursor:], quote=False))

    res = "".join(out)
    res = re.sub(r" +", " ", res)
    res = re.sub(r"\s+([,;:.\?!])", r"\1", res)
    return res


def replace_outside_del_tags(html_text: str, pattern: re.Pattern, repl_fn) -> str:
    """Apply regex replacement to text chunks in an HTML string, skipping text inside <del>...</del>."""
    parts = re.split(r"(<[^>]+>)", html_text)
    in_del = False
    new_parts: List[str] = []
    for p in parts:
        if p.startswith("<"):
            if p.startswith("<del"):
                in_del = True
            elif p.startswith("</del>"):
                in_del = False
            new_parts.append(p)
        else:
            if in_del or not p:
                new_parts.append(p)
            else:
                new_parts.append(pattern.sub(repl_fn, p))
    return "".join(new_parts)


class RevisionTagger:
    """Injects inline strikethrough/revision markup comparing against the 1830 First Edition."""

    def __init__(self, bom_1830_dict: Dict[str, str]):
        self.bom_1830_dict = bom_1830_dict

    def tag_chapter_revisions(self, chapter: Chapter) -> int:
        """Inject 1830 revisions into chapter.verses tagged_html. Returns count of verses with revisions."""
        rev_count = 0
        for verse in chapter.verses:
            t_1830 = self.bom_1830_dict.get(verse.verse_key)
            if not t_1830:
                verse.tagged_html = html.escape(verse.text, quote=False)
                continue

            rev_html = generate_verse_revision(t_1830, verse.text)
            if "<del" in rev_html or "<ins" in rev_html:
                rev_count += 1
            verse.tagged_html = rev_html
        return rev_count


class OnomaMatcher:
    """High-speed regex boundary matcher for Onomasticon lemmas."""

    def __init__(self, onoma_dict: Dict[str, OnomaEntry]):
        self.onoma_dict = onoma_dict
        self._build_patterns()

    def _build_patterns(self):
        # Map each surface form to canonical lemma uppercase
        self.pattern_to_lemma: Dict[str, str] = {}
        patterns: List[str] = []

        for upper_lemma, entry in self.onoma_dict.items():
            base_clean = entry.lemma.strip()
            if not base_clean or len(base_clean) < 2:
                continue

            # Skip generic common English words that might create false positives if lowercase
            # We enforce exact capitalized match for common homonyms
            variations = set()

            # Base title case
            title_case = base_clean.capitalize()
            variations.add(title_case)

            # If lemma has (S) e.g. NEPHITE(S)
            if "(S)" in base_clean.upper():
                root = re.sub(r"\(S\)", "", base_clean, flags=re.I).strip().capitalize()
                variations.add(root)
                variations.add(root + "s")
            elif base_clean.endswith("ITES") or base_clean.endswith("ites"):
                root = base_clean[:-1].capitalize()
                variations.add(root)
                variations.add(base_clean.capitalize())

            # Hyphenated names e.g. Lehi-Nephi
            if "-" in base_clean:
                parts = [p.capitalize() for p in base_clean.split("-")]
                variations.add("-".join(parts))

            for v in variations:
                self.pattern_to_lemma[v] = upper_lemma
                patterns.append(re.escape(v))

        # Sort patterns by length descending so longer compounds match first
        patterns.sort(key=len, reverse=True)

        # Build regex with word boundaries and optional possessives ('s or ’s)
        # Using regex module or standard re
        joined = "|".join(patterns)
        self.regex = re.compile(rf"\b({joined})(?:['’]s)?\b")

    def tag_chapter_verses(self, chapter: Chapter) -> Tuple[Dict[str, OnomaEntry], int]:
        """Tag entity occurrences in chapter verses.

        Tags each distinct entity once per chapter to maintain optimal readability without visual noise.
        """
        tagged_lemmas_in_chapter: Set[str] = set()
        chapter_onoma: Dict[str, OnomaEntry] = {}
        total_tagged = 0

        for verse in chapter.verses:
            verse_html = (
                verse.tagged_html
                if verse.tagged_html
                else html.escape(verse.text, quote=False)
            )

            def replace_entity(match: re.Match) -> str:
                nonlocal total_tagged
                matched_surface = match.group(1)
                full_token = match.group(0)  # includes possessive if present
                upper_lemma = self.pattern_to_lemma.get(matched_surface)
                if not upper_lemma:
                    return full_token

                entry = self.onoma_dict.get(upper_lemma)
                if not entry:
                    return full_token

                slug = slugify_lemma(entry.lemma)
                chapter_onoma[slug] = entry

                # If this lemma was not yet tagged in this chapter, add noteref
                if upper_lemma not in tagged_lemmas_in_chapter:
                    tagged_lemmas_in_chapter.add(upper_lemma)
                    verse.onoma_lemmas.append(entry.lemma)
                    total_tagged += 1
                    ref_id = f"ref-onoma-{slug}"
                    fn_id = f"fn-onoma-{slug}"
                    return f'{full_token}<a epub:type="noteref" class="noteref onoma-ref" href="#{fn_id}" id="{ref_id}"><sup>*</sup></a>'

                return full_token

            verse.tagged_html = replace_outside_del_tags(
                verse_html, self.regex, replace_entity
            )

        chapter.onoma_entries = chapter_onoma
        return chapter_onoma, total_tagged


class CitationTagger:
    """Injects verse-level historical citation footnote references."""

    def __init__(self, citation_dict: Dict[str, List[Citation]]):
        self.citation_dict = deduplicate_citations_to_last_verse(citation_dict)


    def tag_chapter_citations(self, chapter: Chapter) -> int:
        """Inject citation anchors at the end of each verse that has citations."""
        citation_count = 0
        chapter_cits: Dict[str, List[Citation]] = {}

        for verse in chapter.verses:
            cits = self.citation_dict.get(verse.verse_key, [])
            if not cits:
                # Also check alternative hyphenation or 0-padded
                continue

            verse.citations = cits
            citation_count += 1
            ref_id = f"ref-cit-{verse.verse_key}"
            fn_id = f"fn-cit-{verse.verse_key}"
            chapter_cits[verse.verse_key] = cits

            # Append citation reference superscript at verse end
            cit_link = f' <a epub:type="noteref" class="noteref cit-ref" href="#{fn_id}" id="{ref_id}"><sup>[{citation_count}]</sup></a>'
            if verse.tagged_html:
                verse.tagged_html = verse.tagged_html.rstrip() + cit_link
            else:
                verse.tagged_html = verse.text.rstrip() + cit_link

        chapter.citation_map = chapter_cits
        return citation_count


class VariantTagger:
    """Injects textual variant footnote references into verses."""

    def __init__(self, variant_dict: Dict[str, List[TextualVariant]]):
        self.variant_dict = variant_dict

    def tag_chapter_variants(self, chapter: Chapter) -> int:
        """Inject textual variant reference links at verses with known manuscript/1830 variants."""
        variant_count = 0
        chapter_vars: Dict[str, List[TextualVariant]] = {}

        for verse in chapter.verses:
            vars_list = self.variant_dict.get(verse.verse_key, [])
            if not vars_list:
                continue

            verse.variants = vars_list
            variant_count += len(vars_list)
            chapter_vars[verse.verse_key] = vars_list

            ref_id = f"ref-var-{verse.verse_key}"
            fn_id = f"fn-var-{verse.verse_key}"

            # Append variant reference superscript
            var_link = f' <a epub:type="noteref" class="noteref var-ref" href="#{fn_id}" id="{ref_id}"><sup>[v]</sup></a>'
            if verse.tagged_html:
                verse.tagged_html = verse.tagged_html.rstrip() + var_link
            else:
                verse.tagged_html = verse.text.rstrip() + var_link

        chapter.variant_map = chapter_vars
        return variant_count

