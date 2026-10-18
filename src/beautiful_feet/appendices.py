"""Scholarly Appendices Generator for Book of Mormon Early-Source & Onomasticon Study Edition.

Generates:
- Appendix A: Historical Speaker & Source Index (biographical register and scriptural citation index)
- Appendix B: Complete Onomasticon Lexicon & Name Gazetteer (A-Z dictionary of all 376 lemmas)
- Appendix C: Chronology, Plates & Translation Overview
"""

from __future__ import annotations
import html
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from .models import OnomaEntry, Citation


# Biographical metadata for prominent 19th-century speakers
SPEAKER_BIOS: Dict[str, Dict[str, str]] = {
    "Joseph Smith": {
        "title": "Prophet, Seer, and Revelator; First President of the Church",
        "dates": "1805–1844",
        "bio": "Translated the Book of Mormon by the gift and power of God between April and June 1829. Declared the Book of Mormon to be 'the most correct of any book on earth, and the keystone of our religion.'",
    },
    "Brigham Young": {
        "title": "Second President of the Church; Pioneer Leader and Colonizer",
        "dates": "1801–1877",
        "bio": "Led the pioneer migration to the Rocky Mountains. Preached extensively on human moral agency, the prophetic gathering of Israel, and the divine covenants made to the ancient inhabitants of the Americas.",
    },
    "John Taylor": {
        "title": "Third President of the Church; 'The Champion of Liberty'",
        "dates": "1808–1887",
        "bio": "Wounded at Carthage Jail during the martyrdom. Author of 'The Mediation and Atonement'; frequently expounded Nephite constitutional law, the reign of the judges, and Christ's cosmic sacrifice.",
    },
    "Wilford Woodruff": {
        "title": "Fourth President of the Church; Renowned Missionary and Diarist",
        "dates": "1807–1898",
        "bio": "One of the most prolific missionaries in modern history; recorded detailed accounts of early discourses and bore fervent testimony of the angelic restoration of ancient American scriptures.",
    },
    "Lorenzo Snow": {
        "title": "Fifth President of the Church",
        "dates": "1814–1901",
        "bio": "Emphasized divine potential and the law of tithing; expounded on faith, holiness, and the promises of the Book of Mormon to the scattered house of Israel.",
    },
    "Orson Pratt": {
        "title": "Apostle, Mathematician, Historian, and Philosopher",
        "dates": "1811–1881",
        "bio": "Known as the foremost 19th-century scriptural scholar of the Church. Formatted the 1879 edition of the Book of Mormon into modern chapters and verses with extensive cross-references. Delivered over 60 discourses analyzing Nephite prophetic chronology and linguistic markers.",
    },
    "Parley P. Pratt": {
        "title": "Apostle, Poet, and Master Pamphleteer",
        "dates": "1807–1857",
        "bio": "Author of 'A Voice of Warning' (1837) and 'Key to the Science of Theology' (1855). Converted upon reading the Book of Mormon in 1830; expounded the Stick of Joseph in the hands of Ephraim.",
    },
    "George Q. Cannon": {
        "title": "Apostle; Counselor in the First Presidency; Editor and Statesman",
        "dates": "1827–1901",
        "bio": "Founded the Juvenile Instructor and Deseret News publishing enterprises; preached on Nephite education, prophetic integrity, and moral endurance.",
    },
    "Orson Hyde": {
        "title": "President of the Quorum of the Twelve Apostles",
        "dates": "1805–1878",
        "bio": "Dedicated the land of Palestine for the return of the Jews in 1841. Extensively expounded the allegory of the tame and wild olive tree in Jacob 5.",
    },
    "Erastus Snow": {
        "title": "Apostle and Colonizer of Southern Utah and Arizona",
        "dates": "1818–1888",
        "bio": "Pioneer leader who brought the gospel to Scandinavia; preached on the Nephite records, the Holy Spirit, and the establishment of Zion in the tops of the mountains.",
    },
    "Heber C. Kimball": {
        "title": "First Counselor in the First Presidency; Apostolic Pioneer",
        "dates": "1801–1868",
        "bio": "Opened the British Mission in 1837; known for direct, vivid parabolic preaching on spiritual sanctification, the potter's clay, and divine judgment.",
    },
    "George A. Smith": {
        "title": "First Counselor in the First Presidency; Church Historian",
        "dates": "1817–1875",
        "bio": "Cousin of the Prophet Joseph Smith; chronicler of early Church trials and expounder of ancient prophetic fulfillment in modern pioneer gathering.",
    },
    "Charles C. Rich": {
        "title": "Apostle and Pioneer Colonizer of San Bernardino and Bear Lake",
        "dates": "1816–1883",
        "bio": "General and colonizer who taught self-reliance, obedience to covenant, and practical discipleship drawn from the example of Captain Moroni.",
    },
    "Jedediah M. Grant": {
        "title": "Second Counselor in the First Presidency; 'Brigham's Sledgehammer'",
        "dates": "1816–1856",
        "bio": "Fiery orator during the Reformation of 1856; called the Saints to sincere repentance and unfeigned faith modeled after Alma the Younger.",
    },
    "Amasa Lyman": {
        "title": "Early Apostle and Pioneer Colonizer",
        "dates": "1813–1877",
        "bio": "Missionary across the frontier; delivered thoughtful addresses on the divine attributes of justice, mercy, and moral agency.",
    },
    "Franklin D. Richards": {
        "title": "Apostle and Church Historian",
        "dates": "1821–1899",
        "bio": "Compiled the first Pearl of Great Price in Liverpool in 1851; long-time president of the European Mission who expounded the ancient records.",
    },
}

BOOK_CANONICAL_ORDER = [
    "1-ne", "2-ne", "jacob", "enos", "jarom", "omni", "w-of-m",
    "mosiah", "alma", "hel", "3-ne", "4-ne", "morm", "ether", "moroni"
]

BOOK_TITLES = {
    "1-ne": "1 Nephi", "2-ne": "2 Nephi", "jacob": "Jacob", "enos": "Enos",
    "jarom": "Jarom", "omni": "Omni", "w-of-m": "Words of Mormon",
    "mosiah": "Mosiah", "alma": "Alma", "hel": "Helaman", "3-ne": "3 Nephi",
    "4-ne": "4 Nephi", "morm": "Mormon", "ether": "Ether", "moroni": "Moroni"
}


def render_speaker_index_xhtml(citation_dict: Dict[str, List[Citation]]) -> str:
    """Render Appendix A: Comprehensive 19th-Century Historical Speaker & Source Index."""
    # Group citations by speaker
    speaker_cits: Dict[str, List[Tuple[str, Citation]]] = defaultdict(list)
    source_counts: Dict[str, int] = defaultdict(int)

    for v_key, c_list in citation_dict.items():
        for c in c_list:
            spk = c.speaker.strip()
            if not spk:
                spk = "Unknown / General"
            speaker_cits[spk].append((v_key, c))
            source_counts[c.source] += 1

    # Sort speakers alphabetically (with Joseph Smith, Brigham Young, John Taylor, Orson Pratt prioritized or strictly alpha)
    sorted_speakers = sorted(speaker_cits.keys())

    lines: List[str] = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!DOCTYPE html>',
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">',
        "<head>",
        "  <title>Appendix A: Historical Speaker &amp; Source Index</title>",
        '  <link rel="stylesheet" type="text/css" href="../styles/style.css" />',
        "</head>",
        "<body>",
        '  <section epub:type="appendix" class="appendix-section">',
        '    <h1 class="book-title">Appendix A</h1>',
        '    <h2 class="chapter-title">Historical Speaker &amp; Source Index (1830–1930)</h2>',
        '    <div class="ornament">&#10087; &bull; &#10086; &bull; &#10087;</div>',
        "",
        '    <div class="intro-box">',
        '      <h3>The 19th-Century &amp; Early-Era Book of Mormon Discourse Tradition</h3>',
        "      <p>",
        "        During the foundational century of the Restoration (1830–1930), early Church leaders expounded ",
        "        the Book of Mormon with prophetic urgency. Rather than treating it merely as devotional reading, ",
        "        they approached its record as an inspired historical and legal treatise, an apocalyptic warning to the Gentiles, ",
        "        and the definitive theological exposition on the Abrahamic covenant and the atonement of Jesus Christ.",
        "      </p>",
        "      <p>",
        "        This index registers every early Church leader whose sermons and writings on the Book of Mormon are cited ",
        "        in this volume. Each entry summarizes the speaker&rsquo;s ministry, total citations, and an exhaustive ",
        "        tabulation of every Book of Mormon passage they expounded in historical records.",
        "      </p>",
        "    </div>",
        "",
        '    <h3 class="footnotes-title">Corpus Source Summary</h3>',
        '    <ul class="cit-list" style="margin-bottom: 2em;">',
    ]

    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        lines.append(f"      <li><strong>{html.escape(src)}:</strong> {count:,} citations</li>")

    lines.extend([
        "    </ul>",
        "",
        '    <h3 class="footnotes-title">Biographical Directory of Historical Speakers</h3>',
    ])

    for spk in sorted_speakers:
        c_tuples = speaker_cits[spk]
        spk_esc = html.escape(spk)
        spk_id = re.sub(r"[^\w-]", "", spk.lower().replace(" ", "-"))

        # Look up bio
        bio_info = SPEAKER_BIOS.get(spk, {})
        title_esc = html.escape(bio_info.get("title", "19th-Century Church Leader"))
        dates_esc = html.escape(bio_info.get("dates", ""))
        desc_esc = html.escape(bio_info.get("bio", ""))

        # Group verses by Book
        verses_by_book: Dict[str, Set[str]] = defaultdict(set)
        for vk, c in c_tuples:
            parts = vk.split("-")
            b_slug = parts[0] if len(parts) == 3 else "-".join(parts[:-2])
            ch = parts[-2]
            v = parts[-1]
            if c.covered_range and ("–" in c.covered_range or "," in c.covered_range):
                verses_by_book[b_slug].add(f"{ch}:{c.covered_range}")
            else:
                verses_by_book[b_slug].add(f"{ch}:{v}")


        lines.extend([
            f'    <div class="speaker-entry" id="{spk_id}" style="margin-top: 1.8em; padding-bottom: 1.2em; border-bottom: 1px solid #dcd3c5;">',
            f'      <h4 style="font-size: 1.2em; color: #781010; margin-bottom: 0.2em;">{spk_esc} <span style="font-size: 0.85em; font-weight: normal; color: #666;">({dates_esc})</span></h4>' if dates_esc else f'      <h4 style="font-size: 1.2em; color: #781010; margin-bottom: 0.2em;">{spk_esc}</h4>',
            f'      <p style="font-style: italic; color: #444; margin: 0.2em 0 0.5em 0; font-size: 0.92em;">{title_esc} &bull; <strong>{len(c_tuples)}</strong> total citations</p>',
        ])

        if desc_esc:
            lines.append(f'      <p style="font-size: 0.95em; line-height: 1.45; margin: 0.4em 0 0.8em 0;">{desc_esc}</p>')

        lines.append('      <p style="font-size: 0.9em; margin: 0.3em 0;"><strong>Verses Cited:</strong></p>')
        lines.append('      <div style="font-size: 0.88em; line-height: 1.6; margin-left: 0.8em; color: #333;">')

        book_links = []
        for b_slug in BOOK_CANONICAL_ORDER:
            if b_slug in verses_by_book:
                b_name = BOOK_TITLES.get(b_slug, b_slug)
                # Sort verses numerically by chapter, then verse
                sorted_vs = sorted(
                    verses_by_book[b_slug],
                    key=lambda x: (
                        int(x.split(":")[0]) if x.split(":")[0].isdigit() else 0,
                        int(x.split(":")[1]) if len(x.split(":")) > 1 and x.split(":")[1].isdigit() else 0,
                    ),
                )
                vs_str = ", ".join(sorted_vs)
                book_links.append(f"<em>{b_name}</em> {vs_str}")

        lines.append(" &bull; ".join(book_links))
        lines.extend([
            "      </div>",
            "    </div>",
        ])

    lines.extend([
        "  </section>",
        "</body>",
        "</html>",
    ])

    return "\n".join(lines)


def render_onoma_gazetteer_xhtml(onoma_dict: Dict[str, OnomaEntry]) -> str:
    """Render Appendix B: Complete Onomasticon Lexicon & Name Gazetteer."""
    # Sort entries alphabetically by lemma
    sorted_entries = sorted(onoma_dict.values(), key=lambda e: e.lemma.upper())

    # Group by first letter
    letter_groups: Dict[str, List[OnomaEntry]] = defaultdict(list)
    for entry in sorted_entries:
        first_char = entry.lemma[0].upper() if entry.lemma else "A"
        letter_groups[first_char].append(entry)

    lines: List[str] = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!DOCTYPE html>',
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">',
        "<head>",
        "  <title>Appendix B: Onomasticon Lexicon &amp; Gazetteer</title>",
        '  <link rel="stylesheet" type="text/css" href="../styles/style.css" />',
        "</head>",
        "<body>",
        '  <section epub:type="appendix" class="appendix-section">',
        '    <h1 class="book-title">Appendix B</h1>',
        '    <h2 class="chapter-title">Complete Onomasticon Lexicon &amp; Gazetteer</h2>',
        '    <div class="ornament">&#10087; &#8226; &#10086; &#8226; &#10087;</div>',
        "",
        '    <div class="intro-box">',
        '      <h3>Linguistic Structure of Book of Mormon Proper Names</h3>',
        "      <p>",
        "        The <em>Book of Mormon Onomasticon</em> project, hosted by Brigham Young University, ",
        "        catalogs and analyzes every proper name, geographical designation, and specialized term ",
        "        within the Nephite, Lamanite, and Jaredite records. Rather than arbitrary inventions, ",
        "        these 376 terms demonstrate profound Semitic (Hebrew, Aramaic), Egyptian, and ancient Near Eastern ",
        "        etymological roots consistent with Lehi&#8217;s 600 BC Jerusalem heritage and King Mosiah&#8217;s ",
        "        records in reformed Egyptian.",
        "      </p>",
        "      <p>",
        "        This comprehensive gazetteer provides the International Phonetic ",
        "        Alphabet (IPA) pronunciation, grammatical classification, concise definition, and synthesized ",
        "        etymological root analysis for every name in the record.",
        "      </p>",
        "    </div>",
        "",
        '    <!-- Quick Letter Navigation -->',
        '    <div style="text-align: center; margin: 1.5em 0; font-size: 0.95em; line-height: 2;">',
    ]

    alphabet_links = [
        f'<a href="#letter-{letter}" style="text-decoration: none; font-weight: bold; margin: 0 0.3em; color: #0b5394;">{letter}</a>'
        for letter in sorted(letter_groups.keys())
    ]
    lines.append(" &#8226; ".join(alphabet_links))
    lines.append("    </div>\n")

    for letter in sorted(letter_groups.keys()):
        lines.append(f'    <h3 id="letter-{letter}" class="footnotes-title" style="font-size: 1.4em; border-bottom: 2px solid #0b5394; color: #0b5394; margin-top: 2em;">&#8212; {letter} &#8212;</h3>')

        for entry in letter_groups[letter]:
            lemma_esc = html.escape(entry.lemma)
            pron_esc = html.escape(entry.pronunciation) if entry.pronunciation else ""
            class_esc = html.escape(entry.classification) if entry.classification else ""
            def_esc = html.escape(entry.definition) if entry.definition else ""
            summary_esc = html.escape(entry.summary) if entry.summary else ""

            prn_html = f'<span class="onoma-pron" style="font-style: italic; color: #555; margin-left: 0.4em;">/{pron_esc}/</span>' if pron_esc else ""
            cls_html = f'<span class="onoma-class" style="font-size: 0.75em; text-transform: uppercase; background-color: #dbe5ee; color: #1a446c; padding: 0.1em 0.45em; border-radius: 3px; margin-left: 0.5em; letter-spacing: 0.04em;">{class_esc}</span>' if class_esc else ""

            lines.extend([
                f'    <div class="gazetteer-entry" style="margin-bottom: 1.4em; padding-bottom: 0.9em; border-bottom: 1px dotted #ccc;">',
                '      <div style="margin-bottom: 0.25em;">',
                f'        <strong style="font-size: 1.1em; color: #0b5394;">{lemma_esc}</strong>{prn_html}{cls_html}',
                "      </div>",
            ])

            if def_esc:
                lines.append(f'      <p style="font-style: italic; color: #444; font-size: 0.92em; margin: 0.2em 0 0.4em 0;">{def_esc}</p>')

            if entry.etymology_paragraphs:
                for p in entry.etymology_paragraphs:
                    lines.append(f'      <p style="font-size: 0.92em; line-height: 1.45; color: #222; margin: 0.35em 0;">{html.escape(p)}</p>')
            elif summary_esc:
                for p in summary_esc.split("\n\n"):
                    lines.append(f'      <p style="font-size: 0.92em; line-height: 1.45; color: #222; margin: 0.35em 0;">{p}</p>')

            lines.append("    </div>")

    lines.extend([
        "  </section>",
        "</body>",
        "</html>",
    ])

    return "\n".join(lines)


def render_chronology_xhtml() -> str:
    """Render Appendix C: Chronology, Plates & Translation Overview."""
    return """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head>
  <title>Appendix C: Chronology &amp; Plates Overview</title>
  <link rel="stylesheet" type="text/css" href="../styles/style.css" />
</head>
<body>
  <section epub:type="appendix" class="appendix-section">
    <h1 class="book-title">Appendix C</h1>
    <h2 class="chapter-title">Chronology, Plates &amp; Translation Overview</h2>
    <div class="ornament">&#10087; &bull; &#10086; &bull; &#10087;</div>

    <div class="intro-box">
      <h3>The Structural Architecture of the Nephite Records</h3>
      <p>
        The Book of Mormon is a composite record spanning over 2,600 years of civilization across the ancient Americas. 
        Mormon and his son Moroni abridged multiple metal plate libraries into the single gold codex delivered to 
        Joseph Smith on the Hill Cumorah in September 1827.
      </p>
    </div>

    <h3 class="footnotes-title">1. The Four Major Plate Collections</h3>
    <ul class="cit-list" style="line-height: 1.6; margin-bottom: 2em;">
      <li>
        <strong>The Small Plates of Nephi:</strong> Dedicated exclusively to spiritual ministry, revelations, 
        and prophetic discourses (1 Nephi through Omni). Engraved by the early patriarchs (Nephi, Jacob, Enos, Jarom, Omni, Amaleki) 
        and bound directly to Mormon&rsquo;s abridgment without editorial alteration.
      </li>
      <li>
        <strong>The Large Plates of Nephi:</strong> The exhaustive secular, political, and dynastic history kept 
        by the reigning kings and chief judges. Mormon abridged this monumental archive into Mosiah, Alma, Helaman, 
        3 Nephi, 4 Nephi, and Mormon 1&ndash;7.
      </li>
      <li>
        <strong>The Plates of Ether (Twenty-Four Gold Plates):</strong> Discovered by the expedition of Limhi in the 
        northern wilderness (ca. 121 BC). They contain the historical annals of the Jaredite nation from the Tower of Babel 
        to their ultimate annihilation, abridged by Moroni in the Book of Ether.
      </li>
      <li>
        <strong>The Plates of Brass of Laban:</strong> Brought by Lehi&rsquo;s sons from Jerusalem in 600 BC. Written in 
        reformed Egyptian and Hebrew, containing the Five Books of Moses, the record of the Jews from Adam down to Zedekiah, 
        the prophecies of the holy prophets (including Isaiah, Jeremiah, and lost prophets Zenock, Zenos, and Neum), and the 
        genealogy of the tribe of Joseph.
      </li>
    </ul>

    <h3 class="footnotes-title">2. Master Historical Chronology</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 0.9em; margin: 1.5em 0;">
      <thead>
        <tr style="background-color: #eee8dc; border-bottom: 2px solid #8c6d3b;">
          <th style="padding: 0.5em; text-align: left; width: 22%;">Approx. Date</th>
          <th style="padding: 0.5em; text-align: left;">Epoch &amp; Event</th>
          <th style="padding: 0.5em; text-align: left; width: 25%;">Scriptural Source</th>
        </tr>
      </thead>
      <tbody>
        <tr style="border-bottom: 1px solid #ddd;">
          <td style="padding: 0.45em;">ca. 2200 BC</td>
          <td style="padding: 0.45em;">Tower of Babel; Jared and his brother lead colony to the Promised Land.</td>
          <td style="padding: 0.45em;">Ether 1&ndash;3</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd; background-color: #faf8f5;">
          <td style="padding: 0.45em;">600 BC</td>
          <td style="padding: 0.45em;">Reign of King Zedekiah; Lehi departs Jerusalem into the Arabian wilderness.</td>
          <td style="padding: 0.45em;">1 Nephi 1&ndash;2</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
          <td style="padding: 0.45em;">ca. 589 BC</td>
          <td style="padding: 0.45em;">Lehite colony sails across the great waters in the ship constructed by Nephi.</td>
          <td style="padding: 0.45em;">1 Nephi 18</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd; background-color: #faf8f5;">
          <td style="padding: 0.45em;">ca. 588&ndash;570 BC</td>
          <td style="padding: 0.45em;">Nephite-Lamanite schism; Nephi flees into the wilderness and builds a temple.</td>
          <td style="padding: 0.45em;">2 Nephi 5</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
          <td style="padding: 0.45em;">ca. 200 BC</td>
          <td style="padding: 0.45em;">Mosiah I leads righteous Nephites from the land of Nephi; discovers Zarahemla and Mulekites.</td>
          <td style="padding: 0.45em;">Omni 1:12&ndash;19</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd; background-color: #faf8f5;">
          <td style="padding: 0.45em;">ca. 124 BC</td>
          <td style="padding: 0.45em;">King Benjamin&rsquo;s covenant address from the tower at the temple in Zarahemla.</td>
          <td style="padding: 0.45em;">Mosiah 2&ndash;5</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
          <td style="padding: 0.45em;">91 BC</td>
          <td style="padding: 0.45em;">King Mosiah II abolishes the monarchy; inauguration of the Reign of the Judges.</td>
          <td style="padding: 0.45em;">Mosiah 29</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd; background-color: #faf8f5;">
          <td style="padding: 0.45em;">6 BC</td>
          <td style="padding: 0.45em;">Samuel the Lamanite prophesies upon the walls of Zarahemla regarding Christ&rsquo;s birth.</td>
          <td style="padding: 0.45em;">Helaman 13&ndash;16</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
          <td style="padding: 0.45em;">1 AD</td>
          <td style="padding: 0.45em;">The night without darkness; the new star appears; birth of Jesus Christ at Bethlehem.</td>
          <td style="padding: 0.45em;">3 Nephi 1</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd; background-color: #faf8f5;">
          <td style="padding: 0.45em;">34 AD</td>
          <td style="padding: 0.45em;">Great cataclysm and three days of darkness; the Resurrected Christ appears at the Bountiful temple.</td>
          <td style="padding: 0.45em;">3 Nephi 8&ndash;28</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
          <td style="padding: 0.45em;">34&ndash;200 AD</td>
          <td style="padding: 0.45em;">Two centuries of universal peace and Christian communal fellowship among Nephites and Lamanites.</td>
          <td style="padding: 0.45em;">4 Nephi 1</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd; background-color: #faf8f5;">
          <td style="padding: 0.45em;">385 AD</td>
          <td style="padding: 0.45em;">Final apocalyptic battle at the Hill Cumorah; extinction of the Nephite nation.</td>
          <td style="padding: 0.45em;">Mormon 6</td>
        </tr>
        <tr style="border-bottom: 1px solid #ddd;">
          <td style="padding: 0.45em;">421 AD</td>
          <td style="padding: 0.45em;">Moroni seals the sacred records and buries them in the Hill Cumorah.</td>
          <td style="padding: 0.45em;">Moroni 10</td>
        </tr>
        <tr style="background-color: #faf8f5;">
          <td style="padding: 0.45em;">1829 AD</td>
          <td style="padding: 0.45em;">Translation of the Gold Plates by Joseph Smith in Harmony, PA and Fayette, NY.</td>
          <td style="padding: 0.45em;">History of the Church 1</td>
        </tr>
      </tbody>
    </table>

    <h3 class="footnotes-title">3. The 1829 Translation Timeline</h3>
    <p>
      The translation of the Book of Mormon was accomplished at unprecedented speed between April 7 and June 30, 1829 
      (approximately sixty-five working days), averaging eight to ten printed pages per day. 
      Oliver Cowdery served as the primary scribe at the Susquehanna home in Harmony, Pennsylvania, before persecution 
      compelled their relocation to the Peter Whitmer Sr. farm in Fayette, New York.
    </p>
  </section>
</body>
</html>"""
