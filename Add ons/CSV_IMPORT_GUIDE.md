# Bybletoolz CSV Import Guide

This guide describes how to structure CSV files for import into Bybletoolz via:

```
byble import exeg <file.csv> "Source Name"
```

---

## Two Supported Formats

### Format 1 — Simple (Verse-per-row)

Best for commentaries where each note maps to a single verse or short verse range.

**Required columns:**

| Column  | Type    | Description                          |
|---------|---------|--------------------------------------|
| `book`  | text    | Full book name (`Genesis`, `Luke`)   |
| `chapter` | integer | Chapter number                     |
| `verse` | integer | Starting verse number                |
| `text`  | text    | Commentary body                      |

**Optional columns:**

| Column      | Type    | Description                              |
|-------------|---------|------------------------------------------|
| `verse_end` | integer | Ending verse if note spans a range       |

**Example:**

```csv
book,chapter,verse,verse_end,text
Genesis,1,1,5,"In the beginning God created the heavens and the earth..."
Genesis,1,6,8,"The firmament refers to the expanse of sky..."
Luke,1,1,,"The prologue of Luke establishes the author's historical method..."
```

---

### Format 2 — Advanced Structured (Multi-column scope)

Best for academic commentaries where notes span multiple chapters, include book introductions, and were extracted from a PDF via a structuring script. This is the format used by `Andrews OT.csv`.

**Required columns:**

| Column              | Type    | Description                                                                 |
|---------------------|---------|-----------------------------------------------------------------------------|
| `book`              | text    | Full book name (`Genesis`, `Isaiah`)                                        |
| `chapter_start`     | integer | Starting chapter of the note's scope                                        |
| `verse_start`       | integer | Starting verse                                                               |
| `chapter_end`       | integer | Ending chapter (same as `chapter_start` for single-chapter notes)           |
| `verse_end`         | integer | Ending verse                                                                 |
| `assignment_source` | text    | Controls how the row is interpreted (see values below)                       |
| `text`              | text    | Commentary body paragraph                                                    |

**`assignment_source` values:**

| Value              | Meaning                                                             |
|--------------------|---------------------------------------------------------------------|
| `explicit_scope`   | The row's chapter/verse columns are directly filled in              |
| `carried_scope`    | The row inherits scope from the previous `explicit_scope` row       |
| `book_introduction`| The row belongs to the book's introduction (stored at chapter 0)   |
| `unassigned`       | Ignored — front matter, page headers, copyright text, etc.          |

**Multi-paragraph notes:** consecutive rows sharing the same scope are merged into a single note with paragraph breaks (`\n\n`). You do not need to merge them manually.

**Example:**

```csv
book,chapter_start,verse_start,chapter_end,verse_end,assignment_source,text
Genesis,,,,,book_introduction,"Genesis is the foundational book of the Pentateuch..."
Genesis,,,,,book_introduction,"The first eleven chapters describe primeval history..."
Genesis,1,1,1,5,explicit_scope,"In the beginning (v. 1) establishes creation ex nihilo..."
Genesis,1,1,1,5,carried_scope,"The six days of creation form a literary framework..."
Genesis,1,6,1,8,explicit_scope,"The firmament (v. 6) refers to the expanse of sky..."
Isaiah,1,1,1,1,explicit_scope,"Isaiah's opening verse serves as the book's superscription..."
```

---

## Notes on Book Names

Use the full canonical book name as it appears in the database:

```
Genesis, Exodus, Leviticus, Numbers, Deuteronomy, Joshua, Judges,
Ruth, 1 Samuel, 2 Samuel, 1 Kings, 2 Kings, 1 Chronicles, 2 Chronicles,
Ezra, Nehemiah, Esther, Job, Psalms, Proverbs, Ecclesiastes,
Song of Solomon, Isaiah, Jeremiah, Lamentations, Ezekiel, Daniel,
Hosea, Joel, Amos, Obadiah, Jonah, Micah, Nahum, Habakkuk,
Zephaniah, Haggai, Zechariah, Malachi,
Matthew, Mark, Luke, John, Acts, Romans, 1 Corinthians, 2 Corinthians,
Galatians, Ephesians, Philippians, Colossians, 1 Thessalonians,
2 Thessalonians, 1 Timothy, 2 Timothy, Titus, Philemon, Hebrews,
James, 1 Peter, 2 Peter, 1 John, 2 John, 3 John, Jude, Revelation
```

---

## Which Format to Use

| Situation                                          | Use Format       |
|----------------------------------------------------|------------------|
| Simple verse notes, one row per note               | Simple           |
| Notes span multi-verse ranges within one chapter   | Simple (add `verse_end`) |
| Notes span multiple chapters                       | Andrews Structured |
| Book has introductory sections                     | Andrews Structured |
| Data was extracted from a PDF via a script         | Andrews Structured |
| Manually typed or exported from a study app        | Simple           |

---

## Re-importing

Re-importing a source with the same name replaces the previous import entirely. The old notes are deleted before the new ones are inserted.

```
byble import exeg "My Commentary.csv" "Source Name"
```

---

## Checking Coverage After Import

```
byble import list
```

This shows each imported source and which books it covers.
