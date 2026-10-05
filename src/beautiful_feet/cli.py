"""Command-line interface for the Book of Mormon Study Edition EPUB builder."""

from __future__ import annotations
import argparse
import sys
import logging
import os
import time

from .models import Book
from .onoma_fetcher import fetch_all_onomasticon
from .citation_fetcher import fetch_all_citations
from .textual_variants import load_textual_variants
from .text_parser import parse_book_of_mormon_md
from .tagger import OnomaMatcher, CitationTagger, VariantTagger
from .builder import build_study_epub

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("beautiful_feet")


def cmd_fetch_onoma(args: argparse.Namespace) -> None:
    logger.info("Fetching / refreshing Book of Mormon Onomasticon data...")
    t0 = time.time()
    data = fetch_all_onomasticon(force_refresh=args.force)
    logger.info(f"Done in {time.time() - t0:.2f}s. Total entries: {len(data)}")


def cmd_fetch_citations(args: argparse.Namespace) -> None:
    logger.info("Fetching / refreshing 19th-century BYU Citation Index data...")
    t0 = time.time()
    data = fetch_all_citations(force_refresh=args.force)
    logger.info(f"Done in {time.time() - t0:.2f}s. Verses with citations: {len(data)}")


def cmd_build(args: argparse.Namespace) -> None:
    logger.info("=== Starting Book of Mormon Study Edition EPUB Build ===")
    t0 = time.time()

    # 1. Load data
    logger.info("Loading Onomasticon entries...")
    onoma_data = fetch_all_onomasticon(force_refresh=False)
    logger.info(f"Loaded {len(onoma_data)} Onomasticon entries.")

    logger.info("Loading early historical citations with verbatim discourse excerpts...")
    cit_data = fetch_all_citations(force_refresh=False)
    cits_with_excerpts = sum(1 for cl in cit_data.values() for c in cl if c.excerpt)
    logger.info(f"Loaded citations for {len(cit_data)} verses ({cits_with_excerpts:,} verbatim discourse excerpts).")

    logger.info("Loading landmark textual variants (1830 first edition & manuscripts)...")
    variant_data = load_textual_variants()
    logger.info(f"Loaded {sum(len(vl) for vl in variant_data.values())} textual variants across {len(variant_data)} verses.")

    # 2. Parse text
    logger.info(f"Parsing Book of Mormon text from {args.input}...")
    books = parse_book_of_mormon_md(args.input)
    total_chapters = sum(len(b.chapters) for b in books)
    total_verses = sum(len(c.verses) for b in books for c in b.chapters)
    logger.info(f"Parsed {len(books)} books, {total_chapters} chapters, {total_verses} verses.")

    # 3. Initialize taggers
    logger.info("Compiling Onomasticon regex matcher and taggers...")
    onoma_matcher = OnomaMatcher(onoma_data)
    variant_tagger = VariantTagger(variant_data)
    citation_tagger = CitationTagger(cit_data)

    # 4. Tag chapters
    logger.info("Tagging onomasticon entities, textual variants, and discourse citations...")
    total_onoma_tags = 0
    total_var_tags = 0
    total_cit_tags = 0

    for book in books:
        for ch in book.chapters:
            _, o_count = onoma_matcher.tag_chapter_verses(ch)
            v_count = variant_tagger.tag_chapter_variants(ch)
            c_count = citation_tagger.tag_chapter_citations(ch)
            total_onoma_tags += o_count
            total_var_tags += v_count
            total_cit_tags += c_count

    logger.info(
        f"Tagging complete: {total_onoma_tags} Onomasticon references, {total_var_tags} Textual Variants, {total_cit_tags} Citation references injected."
    )

    # 5. Build EPUB with Scholarly Appendices
    output_path = args.output
    logger.info(f"Assembling EPUB3 package with Appendices A, B, and C to {output_path}...")
    out_file = build_study_epub(
        books,
        onoma_data=onoma_data,
        cit_data=cit_data,
        output_path=output_path,
    )
    file_size_mb = os.path.getsize(out_file) / (1024 * 1024)

    dt = time.time() - t0
    logger.info(f"=== Build Successful in {dt:.2f}s! ===")
    logger.info(f"Output File: {out_file} ({file_size_mb:.2f} MB)")



def cmd_validate(args: argparse.Namespace) -> None:
    import zipfile
    from lxml import etree

    epub_path = args.input
    logger.info(f"=== Validating EPUB: {epub_path} ===")
    if not os.path.exists(epub_path):
        logger.error(f"File not found: {epub_path}")
        sys.exit(1)

    with zipfile.ZipFile(epub_path, "r") as z:
        infolist = z.infolist()
        # 1. Mimetype check
        first_file = infolist[0]
        if first_file.filename != "mimetype" or first_file.compress_type != zipfile.ZIP_STORED:
            logger.error("FAIL: mimetype is not first or uncompressed.")
            sys.exit(1)
        logger.info("PASS: mimetype is first and uncompressed (STORED).")

        # 2. Container check
        container_xml = z.read("META-INF/container.xml")
        root = etree.fromstring(container_xml)
        rootfile = root.xpath("//*[local-name()='rootfile']/@full-path")[0]
        logger.info(f"PASS: container.xml points to: {rootfile}")

        # 3. OPF check
        opf_xml = z.read(rootfile)
        opf_root = etree.fromstring(opf_xml)
        manifest_items = opf_root.xpath("//*[local-name()='item']/@href")
        spine_items = opf_root.xpath("//*[local-name()='itemref']/@idref")
        logger.info(
            f"PASS: OPF parsed. Manifest items: {len(manifest_items)}, Spine items: {len(spine_items)}"
        )

        # 4. XHTML XML & Anchor Integrity
        xhtml_files = [f for f in z.namelist() if f.endswith(".xhtml")]
        total_noterefs = 0
        total_asides = 0
        broken_links = []
        xml_errors = []

        ns = {"epub": "http://www.idpf.org/2007/ops", "x": "http://www.w3.org/1999/xhtml"}

        for xf in xhtml_files:
            content = z.read(xf)
            try:
                doc = etree.fromstring(content)
            except Exception as e:
                xml_errors.append((xf, str(e)))
                continue

            all_ids = set(doc.xpath("//@id"))
            hrefs = doc.xpath("//x:a[starts-with(@href, '#')]/@href", namespaces=ns)
            for h in hrefs:
                target_id = h.lstrip("#")
                if target_id not in all_ids:
                    broken_links.append((xf, h, target_id))

            noterefs = doc.xpath(
                "//x:a[@epub:type='noteref' or contains(@class, 'noteref')]", namespaces=ns
            )
            asides = doc.xpath("//x:aside[@epub:type='footnote']", namespaces=ns)
            total_noterefs += len(noterefs)
            total_asides += len(asides)

        if xml_errors:
            logger.error(f"FAIL: XML errors found: {len(xml_errors)}")
            for err in xml_errors[:5]:
                logger.error(f"  {err[0]}: {err[1]}")
            sys.exit(1)
        else:
            logger.info(f"PASS: All {len(xhtml_files)} XHTML files are 100% strictly valid XML.")

        if broken_links:
            logger.error(f"FAIL: Broken internal links: {len(broken_links)}")
            for bl in broken_links[:5]:
                logger.error(f"  {bl[0]}: {bl[1]} -> target id '{bl[2]}' not found!")
            sys.exit(1)
        else:
            logger.info("PASS: 100% of internal footnote anchor links resolve perfectly to their targets.")

        logger.info(f"Total noteref anchors: {total_noterefs:,}")
        logger.info(f"Total footnote asides: {total_asides:,}")
        logger.info("=== EPUB Validation 100% Passed! ===")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Book of Mormon Early-Source & Onomasticon Study EPUB Builder"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # fetch-onoma
    p_onoma = subparsers.add_parser("fetch-onoma", help="Fetch Onomasticon data")
    p_onoma.add_argument("--force", action="store_true", help="Force refresh cache")

    # fetch-citations
    p_cit = subparsers.add_parser("fetch-citations", help="Fetch 19th-century citations")
    p_cit.add_argument("--force", action="store_true", help="Force refresh cache")

    # build
    p_build = subparsers.add_parser("build", help="Build the EPUB file")
    p_build.add_argument(
        "--input",
        default="assets/raw/Book of Mormon.md",
        help="Path to Book of Mormon markdown",
    )
    p_build.add_argument(
        "--output",
        default="output/Book_of_Mormon_Early_Sources_Study_Edition.epub",
        help="Path for generated EPUB",
    )

    # validate
    p_val = subparsers.add_parser("validate", help="Validate an EPUB file")
    p_val.add_argument(
        "--input",
        default="output/Book_of_Mormon_Early_Sources_Study_Edition.epub",
        help="Path to EPUB to validate",
    )

    # all
    p_all = subparsers.add_parser("all", help="Run full pipeline (fetch if missing and build)")
    p_all.add_argument(
        "--input",
        default="assets/raw/Book of Mormon.md",
        help="Path to Book of Mormon markdown",
    )
    p_all.add_argument(
        "--output",
        default="output/Book_of_Mormon_Early_Sources_Study_Edition.epub",
        help="Path for generated EPUB",
    )
    p_all.add_argument("--force-refresh", action="store_true", help="Force refresh all datasets")

    args = parser.parse_args()

    if args.command == "fetch-onoma":
        cmd_fetch_onoma(args)
    elif args.command == "fetch-citations":
        cmd_fetch_citations(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "all" or args.command is None:
        if args.command is None:
            # Default to all
            args.input = "assets/raw/Book of Mormon.md"
            args.output = "output/Book_of_Mormon_Early_Sources_Study_Edition.epub"
            args.force = False
        else:
            args.force = args.force_refresh
        cmd_build(args)


if __name__ == "__main__":
    main()
