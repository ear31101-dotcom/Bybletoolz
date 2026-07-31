# Bybletoolz Manual

Bybletoolz is a local Bible study tool for the terminal. It stores the full Bible text in five public-domain translations, Strong's Hebrew and Greek lexicons enriched with Brown-Driver-Briggs and Thayer's definitions, morphological word tagging, and 430,000+ cross-references in a single local SQLite database. No internet connection is needed after the initial setup — all data stays on your machine.

Four study modes are available: **Lex** looks up original-language word meanings via Strong's numbering; **Con** traces a word across the entire Bible by its Hebrew or Greek root; **Cross** surfaces thematically and textually linked passages; and **Exeg** displays verse-by-verse commentary from sources you import. An import system supports bringing in custom cross-references, lexicon entries, and commentary from CSV/TSV files or e-Sword SQLite modules — including commercial resources such as BDAG, Zodhiates, or the Andrews University Commentary.

---

## Setup

### Requirements
- Python 3.10 or later
- Internet connection (first run only, to download source data)

### First-Time Setup

Navigate to the project folder and build the database:

```bash
cd /Users/eric/Code/Bybletoolz
python setup/build_db.py
```

This downloads all source data and creates `bible.db` (~60 MB). It only needs to be run once.

### Running the Tool

Commands use the `byble` alias (set up during installation):

```bash
byble <reference> [mode] [options]
```

If the alias isn't available yet, open a new terminal window. If you ever need to reinstall it:

```bash
echo "alias byble='/Users/eric/Code/Bybletoolz/.venv/bin/python /Users/eric/Code/Bybletoolz/study.py'" >> ~/.zshrc && source ~/.zshrc
```

---

## Command Reference

### General Syntax

```
byble <Book> <Chapter>:<Verse> [Translation] [Mode] [Option]
```

- **Book** — full name or abbreviation (see Book Abbreviations below)
- **Chapter:Verse** — e.g. `1:1` or `1:5-12` for a range
- **Translation** — `KJV`, `ASV`, `BSB`, `YLT`, or `BBE` (default: `KJV`)
- **Mode** — `Lex`, `Con`, `Cross`, or `Exeg` (omit to display passage only)
- **Option** — depends on mode (see below)

---

## Translations

Five public-domain translations are available. Translation tokens are case-insensitive.

| Code | Translation | Character | Best For |
|---|---|---|---|
| `KJV` | King James Version (1611) | Formal, poetic | Default — classic literary text |
| `ASV` | American Standard Version (1901) | Formal, precise | Word studies — very literal, close to Hebrew/Greek |
| `BSB` | Berean Standard Bible (2020) | Modern, readable | Everyday reading — closest free alternative to NIV/NASB |
| `YLT` | Young's Literal Translation (1898) | Extremely literal | Deep study — preserves Hebrew tense and idiom |
| `BBE` | Bible in Basic English (1949) | Simplified | Accessibility — plain vocabulary, easy to follow |

**Note:** NKJV, NASB, NIV, and NLT are under active copyright and cannot be included in a local tool. ASV and BSB are the closest freely available equivalents.

---

## Modes

### Passage Display (no mode)

Displays a verse, passage range, or full chapter. Add a translation code to switch versions.

```bash
byble John 3:16
byble John 3:16 BSB
byble John 3:16 YLT
byble Gen 1:1-5 ASV
byble John 3
byble Gen 1 BSB
```

---

### Lex — Lexicon Mode

Looks up the original Hebrew (OT) or Greek (NT) meaning of words in a verse. Lex always uses KJV word tagging regardless of translation.

**Full verse** — shows every word's Strong's entry in a table:
```bash
byble Gen 1:1 Lex
```

**Single English word** — finds the best matching Strong's entry for that word:
```bash
byble Gen 1:1 Lex created
byble John 3:16 Lex loved
```

**Direct Strong's number at verse scope** — looks up a specific entry, bypassing word matching:
```bash
byble Gen 1:1 Lex H7225
byble John 1:1 Lex G3056
```

**Direct Strong's number at chapter or book scope** — shows the lexicon definition plus every verse in that scope where the number appears:
```bash
byble Gen 1 Lex H7225        Definition + all occurrences of H7225 in Genesis chapter 1
byble Gen Lex H7225           Definition + all occurrences of H7225 in Genesis
```

The output leads with the full lexicon entry (gloss, root, BDB/Thayer's definition), followed by an occurrence table — verse reference and full KJV text — for every verse in the scope containing that word.

> **Tip:** Use Strong's numbers when an English word lookup returns an unexpected result.
> Hebrew numbers use the `H` prefix (H1–H8674). Greek numbers use the `G` prefix (G1–G5624).
> Old Testament verses search Hebrew entries first. New Testament verses search Greek entries first.

---

### Con — Concordance Mode

Finds every verse sharing the same Hebrew or Greek root word (via Strong's number), with optional scope limiting. Results are drawn from KJV text.

**Word in command:**
```bash
byble Exo 20:1 Con spake
byble John 3:16 Con loved
```

**Prompt fallback** — if no word is given, the tool prints the verse and asks:
```bash
byble Exo 20:1 Con
```

**Scoped search by Strong's number:**
```bash
byble Gen 1:1 Con H7225       Occurrences in a specific verse
byble Gen 1 Con H7225         Occurrences in Genesis chapter 1
byble Gen Con H7225           Occurrences in the whole book of Genesis
byble Con H7225               Occurrences across the full Bible
```

**Scoped search by English word** — the tool resolves the word to its most likely Strong's number within the given scope, then searches by that number:
```bash
byble Gen 1 Con created       Resolves "created" → H1254 (bara), then searches Genesis 1
byble Rev 14 Con third        Resolves "third" → G5154 (tritos), then searches Revelation 14
byble Gen Con created         Resolves within Genesis, then searches the whole book
```

At verse scope, the word is matched against Strong's entries tagged in that exact verse. At chapter or book scope, the tool finds the Strong's number whose gloss matches the word and which appears most frequently in verses where the KJV text contains that English word — this intersection avoids common grammatical particles that would otherwise rank higher by frequency alone.

> **Tip:** When an English word resolves to an unexpected root, use a Strong's number directly for a precise search (`Con H1254`).

Output includes:
- Every verse in scope containing that word, with the keyword highlighted in context
- A book frequency bar chart showing where the word clusters
- Pagination — press `n` for next page, `q` to quit

---

### Cross — Cross-Reference Mode

Finds passages thematically or textually linked to the given verse or passage.

**Flat output** (default):
```bash
byble Gen 1:1-2 Cross
byble Gen 1:1-2 Cross flat
```

**Grouped output** — results organized under each source verse:
```bash
byble Gen 1:1-2 Cross grp
```

> Cross-reference data comes from the scrollmapper database (340,000+ links).

---

### Exeg — Exegesis Mode

Displays verse-by-verse commentary from imported scholarly sources. No commentary is bundled by default — see **Importing Custom Data** below to add sources.

**Show book introduction** — displays the imported book-level introduction or overview for that book:
```bash
byble Gen Exeg
byble Isa Exeg
```

**Show all imported commentaries for a verse:**
```bash
byble Gen 1:1 Exeg
byble Rom 8:28-30 Exeg
```

**Show all commentary for an entire chapter** — displays the full chapter text, then notes grouped by verse:
```bash
byble Gen 1 Exeg
byble Rom 8 Exeg
```

**Filter to a specific source:**
```bash
byble Gen 1:1 Exeg "Matthew Henry"
byble Gen 1 Exeg "SDA Bible Commentary"
```

At verse or range scope, output is grouped by source with verse labels. At chapter scope, output is grouped by verse with the source name shown under each verse — useful for reading through a chapter's commentary in canonical order.

**Recommended public domain sources** (free to download as e-Sword `.cmtx` modules from e-sword.net):

| Source | Coverage | Strength |
|--------|----------|----------|
| Matthew Henry's Commentary | Full Bible | Devotional depth, pastoral warmth |
| Adam Clarke's Commentary | Full Bible | Original language analysis |
| Albert Barnes' Notes | Full Bible | Clear, accessible scholarship |
| Jamieson-Fausset-Brown | Full Bible | Concise critical notes |
| Keil & Delitzsch | OT only | Hebrew/scholarly depth |
| Vincent's Word Studies | NT only | Exceptional Greek word analysis |
| Robertson's Word Pictures | NT only | Greek grammar depth |

---

## Book Abbreviations

The tool accepts full book names or common abbreviations. Case is not sensitive.

| Book | Abbreviations |
|---|---|
| Genesis | Gn, Gen |
| Exodus | Ex, Exo |
| Leviticus | Lv, Lev |
| Numbers | Nu, Num |
| Deuteronomy | Dt, Deu, Deut |
| Joshua | Jos |
| Judges | Jdg |
| Ruth | Rut |
| 1 Samuel | 1Sa, 1Sam |
| 2 Samuel | 2Sa, 2Sam |
| 1 Kings | 1Ki, 1Kgs |
| 2 Kings | 2Ki, 2Kgs |
| 1 Chronicles | 1Ch, 1Chr |
| 2 Chronicles | 2Ch, 2Chr |
| Ezra | Ezr |
| Nehemiah | Neh |
| Esther | Est |
| Job | Job |
| Psalms | Ps, Psa, Psalm |
| Proverbs | Pro, Prov |
| Ecclesiastes | Ecc, Eccl |
| Song of Solomon | Sng, Song |
| Isaiah | Is, Isa |
| Jeremiah | Jer |
| Lamentations | Lam |
| Ezekiel | Eze, Ezk |
| Daniel | Dan |
| Hosea | Hos |
| Joel | Joe |
| Amos | Amo |
| Obadiah | Oba |
| Jonah | Jon |
| Micah | Mic |
| Nahum | Nam |
| Habakkuk | Hab |
| Zephaniah | Zep |
| Haggai | Hag |
| Zechariah | Zec, Zech |
| Malachi | Mal |
| Matthew | Mt, Mat, Matt |
| Mark | Mk, Mar |
| Luke | Lk, Luk |
| John | Jn, Joh |
| Acts | Ac, Act |
| Romans | Rom |
| 1 Corinthians | 1Co, 1Cor |
| 2 Corinthians | 2Co, 2Cor |
| Galatians | Gal |
| Ephesians | Eph |
| Philippians | Php, Phil |
| Colossians | Col |
| 1 Thessalonians | 1Th, 1Thes |
| 2 Thessalonians | 2Th, 2Thes |
| 1 Timothy | 1Ti, 1Tim |
| 2 Timothy | 2Ti, 2Tim |
| Titus | Tit |
| Philemon | Phm |
| Hebrews | Heb |
| James | Jas |
| 1 Peter | 1Pe, 1Pet |
| 2 Peter | 2Pe, 2Pet |
| 1 John | 1Jo, 1Jn |
| 2 John | 2Jo, 2Jn |
| 3 John | 3Jo, 3Jn |
| Jude | Jud |
| Revelation | Rv, Rev |

---

## Importing Custom Data

You can supplement the built-in data with your own cross-references, lexicon entries, or commentary from any source — including commercial and personal resources.

### Commands

```
byble import xref  <file> ["Source Name"]   Import cross-references
byble import lex   <file> ["Source Name"]   Import lexicon entries
byble import exeg  <file> ["Source Name"]   Import commentary for Exeg mode
byble import list                           List all imported sources with coverage
byble import remove "Source Name"           Remove an imported source
```

Custom data is stored separately from built-in data and is always merged at query time. Custom lexicon entries take priority over built-in Strong's entries for the same Strong's number. Custom cross-references are deduplicated against the built-in set. Multiple commentary sources can be imported simultaneously and all appear in Exeg output.

### Coverage tracking

When you import commentary, the tool automatically scans what was loaded and records the book coverage for that source. You do not need to declare coverage manually.

`byble import list` shows each commentary source with its coverage summary:

```
Commentary sources:
  Matthew Henry        — 31,102 notes  (Full Bible)
  Keil & Delitzsch     —  8,943 notes  (OT only)
  Vincent's Word Stud  —  3,566 notes  (NT only)
  Andrews University   —  4,201 notes  (Matthew, Mark, Luke, John … (12 books))
  My Romans Notes      —      3 notes  (Romans)
```

Coverage labels:
- **Full Bible** — all 66 books present
- **OT only** — all 39 OT books present
- **NT only** — all 27 NT books present
- **Named books** — up to 5 book names listed; beyond that, summarized as `… (N books)`

When you run `byble ... Exeg`, sources that have no note for the current verse are listed in dim text at the bottom of the output so you can see they were checked — not missing. This is especially useful when working with single-book or partial commentaries:

```
  My Romans Notes (Romans) — no note for John 3:16
  Keil & Delitzsch (OT only) — no note for John 3:16
```

### Supported file formats

**CSV / TSV** — works for cross-references, lexicons, and commentary. The file must have a header row. Comma or tab delimiter is detected automatically.

Cross-reference columns:
```
from_book, from_chapter, from_verse, to_book, to_chapter, to_verse[, notes]
```
Example:
```
from_book,from_chapter,from_verse,to_book,to_chapter,to_verse,notes
John,3,16,Romans,5,8,God's love demonstrated
Genesis,1,1,John,1,1,In the beginning
```

Lexicon columns:
```
number, gloss, definition[, language, word, transliteration, root]
```
`number` must be Strong's format: H1, H7225, G3056, etc. `language` defaults to Hebrew for H-numbers and Greek for G-numbers if omitted.

Example:
```
number,gloss,definition,language
H7225,beginning,"The first in order or rank; chief, choicest part",Hebrew
G3056,word,"The divine logos; reason, discourse, or the Word of God",Greek
```

Commentary columns:
```
book, chapter, verse, text[, verse_end]
```
`verse_end` is optional. Omit it (or leave blank) for single-verse notes. Set it when a commentary note covers a span of verses within the same chapter — the note will then appear for any verse in that range.

Example:
```
book,chapter,verse,verse_end,text
Genesis,1,1,5,"Verses 1–5 — The creation account opens with bereshit..."
Romans,8,28,30,"The golden chain — verses 28–30 form a single theological unit..."
Romans,8,31,,"If God is for us — a standalone note on verse 31"
```

For notes that span multiple chapters, use the Andrews structured layout instead (see XLSX section below).

**XLSX / CSV (structured)** — Three layouts are auto-detected by column headers:

*Standard layout* — `book, chapter, verse, text` (plus optional `verse_end`). Same structure as the plain CSV format above. Works as both CSV and XLSX.

*Embedded-verse layout* — `section, chapter, text` where each text cell begins with a verse reference (`1`, `1-3`, `16, 17`, etc.). Continuation paragraphs with no leading verse ref are merged into the preceding note. Matches the SDA Bible Commentary export format.
```
byble import exeg  sda_bible_commentary.xlsx  "SDA Bible Commentary"
```

*Andrews structured layout* — `book, chapter_start, verse_start, chapter_end, verse_end, assignment_source, text`. Used by the Andrews Bible Commentary structured export and similar scholarly commentary exports where each paragraph carries explicit scope metadata. Only rows with `assignment_source` of `explicit_scope` or `carried_scope` are imported; paragraphs sharing the same scope are merged into a single note. Supports cross-chapter ranges (e.g. `Genesis 1:1–11:26`). Works as both CSV and XLSX.
```
byble import exeg  andrews_ot_structured.xlsx  "Andrews OT Commentary"
byble import exeg  andrews_ot_structured.csv   "Andrews OT Commentary"
```

**e-Sword SQLite** — for modules downloaded or purchased through e-Sword (e-sword.net):

- Cross-references: `.refi` files
- Lexicons: `.dct` files (e.g. BDAG, Mounce, Zodhiates)
- Commentary: `.cmtx` files (e.g. Matthew Henry, Adam Clarke, Albert Barnes, Andrews University)

Just point the import command at the file:
```
byble import xref  my_crossrefs.refi    "Treasury of Scripture Knowledge"
byble import lex   bdag.dct             "BDAG Greek Lexicon"
byble import exeg  matthew_henry.cmtx   "Matthew Henry"
byble import exeg  andrews.cmtx         "Andrews University Commentary"
```

### Notes

- Source names are how you identify and remove imports — choose something descriptive.
- Removing a source deletes only that source's data; built-in data is never affected.
- Book names in CSV files must match the full names used by this tool (e.g. `1 Samuel`, `Song of Solomon`).
- A single-book commentary (e.g. a Romans commentary) imports perfectly — coverage will show `Romans` and Exeg will display its notes only for Romans verses.

---

## Data Sources

All data is public domain or openly licensed.

| Data | Source | License |
|---|---|---|
| Bible text — KJV | [aruljohn/Bible-kjv](https://github.com/aruljohn/Bible-kjv) | Public Domain |
| Bible text — ASV, BSB, YLT, BBE | [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) | Public Domain / CC BY |
| Hebrew lexicon (base) | [openscriptures/strongs](https://github.com/openscriptures/strongs) | Public Domain |
| Greek lexicon (base) | [openscriptures/strongs](https://github.com/openscriptures/strongs) | Public Domain |
| Hebrew definitions (BDB) | [STEPBible TBESH](https://github.com/STEPBible/STEPBible-Data) — Brown-Driver-Briggs tradition | CC BY 4.0 |
| Greek definitions (Thayer's) | [STEPBible TBESG](https://github.com/STEPBible/STEPBible-Data) — Abbott-Smith / Thayer's tradition | CC BY 4.0 |
| Hebrew word tagging | [openscriptures/morphhb](https://github.com/openscriptures/morphhb) | CC BY 4.0 |
| Greek word tagging | [STEPBible/STEPBible-Data](https://github.com/STEPBible/STEPBible-Data) | CC BY 4.0 |
| Cross-references | [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) | Public Domain |

---

## Known Limitations

- **Single-word Lex by English** — word matching searches Strong's gloss text. Words whose gloss does not use the exact English term (e.g. "beginning" → H7225 glossed as "the first") will not match. Use a Strong's number directly in those cases (`Lex H7225`).
- **Lex and Con always use KJV** — word tagging is aligned to KJV text. Switching translation affects passage display only.
- **Passage ranges** — cross-chapter ranges (e.g. `1:30-2:5`) are not yet supported. Use same-chapter ranges only.

---

## Quick Reference Card

```
Passage (KJV)     byble John 3:16
Passage (BSB)     byble John 3:16 BSB
Passage (YLT)     byble John 3:16 YLT
Passage range     byble Gen 1:1-5 ASV
Passage chapter   byble John 3
Chapter (BSB)     byble Gen 1 BSB

Lex full verse    byble Gen 1:1 Lex
Lex by word       byble Gen 1:1 Lex created
Lex by number     byble Gen 1:1 Lex H7225
Lex chapter scope byble Gen 1 Lex H7225
Lex book scope    byble Gen Lex H7225

Concordance       byble Exo 20:1 Con spake
Con (prompt)      byble Exo 20:1 Con
Con chapter scope byble Gen 1 Con H7225
Con chapter word  byble Gen 1 Con created
Con book scope    byble Gen Con H7225
Con book word     byble Gen Con created
Con full Bible    byble Con H7225

Cross flat        byble Gen 1:1-2 Cross
Cross grouped     byble Gen 1:1-2 Cross grp

Exeg book intro   byble Gen Exeg
Exeg verse        byble Gen 1:1 Exeg
Exeg chapter      byble Gen 1 Exeg
Exeg one source   byble Gen 1:1 Exeg "Matthew Henry"

Import xref       byble import xref  file.csv   "Source Name"
Import lexicon    byble import lex   file.csv   "Source Name"
Import commentary byble import exeg  file.cmtx  "Source Name"
List imports      byble import list
Remove import     byble import remove "Source Name"
```
