# Modules — Architecture Overview

This folder contains all study mode logic for Bybletoolz. Each module is responsible for one concern and communicates through a shared `parsed` dictionary produced by `parser.py`.

---

## Request Lifecycle

```
study.py  →  parser.py  →  [mode module]  →  SQLite (bible.db)  →  rich terminal output
```

1. `study.py` receives raw CLI arguments (`sys.argv`)
2. `parser.py` validates and structures them into a `parsed` dict
3. `study.py` routes to the correct mode module based on `parsed["mode"]`
4. The mode module queries `bible.db` and renders output via the `rich` library

---

## `parser.py`

Parses raw CLI tokens into a structured dict:

```python
{
    "book":        str | None,   # e.g. "Genesis"
    "chapter":     int | None,
    "verse_start": int | None,
    "verse_end":   int | None,
    "mode":        str | None,   # "lex" | "con" | "cross" | "exeg" | None
    "word":        str | None,   # Strong's number or English word
    "cross_style": str,          # "flat" | "grp"
    "translation": str,          # "KJV" | "ASV" | "BSB" | "YLT" | "BBE"
    "error":       str | None,
}
```

Supports five reference scopes:

| Input | Scope |
|-------|-------|
| `byble Gen Exeg` | Book only |
| `byble Gen 1 Exeg` | Chapter only |
| `byble Gen 1:1 Lex` | Single verse |
| `byble Gen 1:1-5 Con` | Verse range |
| `byble Con H7225` | Mode-first, no reference |

---

## `passage.py`

Renders Bible text with no mode keyword. Handles single verse, verse range, and full chapter display. Respects the `translation` field.

**Key tables:** `verses`

---

## `lex.py` — Lexicon

Displays the original Hebrew or Greek words for a verse, with Strong's numbers, transliteration, gloss, and full BDB/Thayer definitions.

Supports scoped lookups:
- Verse scope: shows the word's entry from the lexicon
- Chapter/book scope: also lists every verse in that scope where the word appears

**Key tables:** `verse_words`, `strongs`, `verses`

---

## `con.py` — Concordance

Traces a Hebrew or Greek root across the Bible by Strong's number or by resolving an English word to its root within the current scope.

English-to-Strong's resolution uses a combined text + gloss filter to avoid false matches (e.g. accusative particles that appear in every verse).

**Key tables:** `verse_words`, `strongs`, `verses`

---

## `cross.py` — Cross-References

Displays thematically and textually linked passages for a verse or range. Supports flat list (`flat`) and grouped-by-source (`grp`) display styles.

**Key tables:** `cross_references`

---

## `exeg.py` — Exegesis / Commentary

Displays imported commentary notes matched to the requested scope. Three scope modes:

| Scope | Query logic |
|-------|-------------|
| Book (`byble Gen Exeg`) | Fetches notes stored at `chapter=0, verse=0` (book introductions) |
| Chapter (`byble Gen 1 Exeg`) | Fetches notes where `chapter <= target <= chapter_end` |
| Verse/range | Fetches notes overlapping `[v_start, v_end]` using `(chapter * 1000 + verse)` arithmetic for cross-chapter ranges |

Performs a migration check at runtime to add `verse_end` and `chapter_end` columns if the database predates them.

**Key tables:** `commentary`, `commentary_sources`

---

## `importer.py`

Handles all `byble import` subcommands. Detects file format automatically:

| Format | Detection |
|--------|-----------|
| Simple CSV | `book`, `chapter`, `verse`, `text` columns present |
| Advanced Structured CSV | `chapter_start` column present |
| XLSX | `.xlsx` file extension (same layout detection inside) |
| e-Sword commentary (`.cmtx`) | SQLite file with `Commentary` table |

Re-importing a source with the same name deletes the old notes first before inserting the new ones.

**Key tables:** `commentary`, `commentary_sources`, `cross_references`, `custom_strongs`

---

## Database Schema (Key Tables)

| Table | Description |
|-------|-------------|
| `verses` | Full Bible text across all translations |
| `verse_words` | Word-level tagging with Strong's numbers |
| `strongs` | Strong's Hebrew and Greek lexicon entries |
| `cross_references` | 430,000+ verse cross-reference pairs |
| `commentary` | Imported exegetical notes (verse/range anchored) |
| `commentary_sources` | Metadata and book coverage per imported source |

---

## Adding a New Mode

1. Create `modules/mymode.py` with a `display(parsed, db_path)` function
2. Add the mode keyword to `MODES` in `parser.py`
3. Add a routing branch in `study.py`
