# Bybletoolz

A local terminal-based Bible study tool. Stores the full Bible text, Strong's Hebrew and Greek lexicons, morphological word tagging, and 430,000+ cross-references in a single SQLite database. No internet connection needed after setup — all data stays on your machine.

## Features

| Mode  | Command example          | What it does                                          |
|-------|--------------------------|-------------------------------------------------------|
| **Passage** | `byble Gen 1:1`      | Display a verse, verse range, or full chapter         |
| **Lex**     | `byble Gen 1:1 Lex`  | Look up original-language words via Strong's numbers  |
| **Con**     | `byble Gen 1:1 Con bara` | Trace a Hebrew/Greek root across the Bible        |
| **Cross**   | `byble Gen 1:1 Cross` | Show cross-references linked to a verse              |
| **Exeg**    | `byble Gen 1:1 Exeg` | Display imported commentary for a verse, chapter, or book |

## Setup

**Requirements:** Python 3.10+

```bash
git clone https://github.com/ear31101-dotcom/Bybletoolz.git
cd Bybletoolz
python -m venv .venv && source .venv/bin/activate
pip install rich openpyxl
python setup/build_db.py
```

This downloads all source data and builds `bible.db` locally. Run once.

### Shell alias (optional)

Add to your `.zshrc` or `.bashrc`:

```bash
alias byble="cd /path/to/Bybletoolz && .venv/bin/python study.py"
```

## Translations

Five public-domain translations are included: `KJV`, `ASV`, `BSB`, `YLT`, `BBE`

```bash
byble John 3:16 YLT
```

## Importing Commentary (Exeg)

Import any CSV or XLSX commentary source:

```bash
byble import exeg "Add ons/my_commentary.csv" "Source Name"
byble import list
```

See [`Add ons/CSV_IMPORT_GUIDE.md`](Add%20ons/CSV_IMPORT_GUIDE.md) for how to structure import files.

## Add-ons Included

| File | Description |
|------|-------------|
| `Add ons/<your_commentary>.csv` | Commentary in Advanced Structured format (see Add ons/CSV_IMPORT_GUIDE.md) |
| `Add ons/sda_bible_commentary.csv` | SDA Bible Commentary verse notes |

> **Note:** `bible.db` and the `data/` folder are not tracked in git (too large). Run `setup/build_db.py` to generate them locally.

## Full Documentation

See [MANUAL.md](MANUAL.md) for complete command reference.
