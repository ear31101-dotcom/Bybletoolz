#!/usr/bin/env python3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "bible.db")

sys.path.insert(0, os.path.dirname(__file__))

from modules.parser import parse_input
from modules import passage, lex, con, cross, exeg, importer


def main():
    if len(sys.argv) < 2:
        print("""
  Bybletoolz — a local Bible study tool for the terminal.

  It stores the full Bible text (5 translations), Strong's Hebrew and Greek
  lexicons (with BDB and Thayer's definitions), morphological word tagging,
  and 430,000+ cross-references in a single local database. No internet
  connection is needed after setup. Study modes let you look up original
  language word meanings, trace a word across the whole Bible, find
  cross-referenced passages, and display verse-by-verse commentary from
  imported sources. All data stays on your machine.

  Usage:  byble <Book> <Chapter>:<Verse> [Translation] [Mode] [Option]

  ── Passage ──────────────────────────────────────────────
  byble Jn 3:16                     Display verse (KJV)
  byble Jn 3:16 BSB                 Display verse in a specific translation
  byble Gen 1:1-5 ASV               Display a verse range

  ── Lex — original language lexicon ─────────────────────
  byble Gen 1:1 Lex                 Show all words with Strong's data
  byble Gen 1:1 Lex created         Look up a specific English word
  byble Gen 1:1 Lex H7225           Look up by Strong's number (verse)
  byble Gen 1 Lex H7225             Look up + occurrences in a chapter
  byble Gen Lex H7225               Look up + occurrences in a book

  ── Con — concordance ────────────────────────────────────
  byble Exo 20:1 Con spake          Find every verse sharing the same root word
  byble Exo 20:1 Con                (prompts for word if omitted)
  byble Gen 1 Con H7225             Scope search to a chapter
  byble Gen Con H7225               Scope search to a book
  byble Con H7225                   Search full Bible by Strong's number

  ── Cross — cross-references ─────────────────────────────
  byble Gen 1:1-2 Cross             Flat list of cross-references (default)
  byble Gen 1:1-2 Cross grp         Grouped by source verse

  ── Exeg — exegesis / commentary ─────────────────────────
  byble Gen 1:1 Exeg                Show all imported commentaries
  byble Gen 1:1 Exeg "Matthew Henry" Filter to one source

  ── Import — add custom data ─────────────────────────────
  byble import exeg  file.cmtx  "Matthew Henry"   Commentary (e-Sword or CSV)
  byble import xref  file.csv   "My Cross-Refs"   Cross-references
  byble import lex   file.csv   "My Lexicon"       Lexicon entries
  byble import list                                List sources with coverage
  byble import remove "Source Name"                Remove a source
""")
        sys.exit(0)

    if not os.path.exists(DB_PATH):
        print("\n  bible.db not found. Run the setup first:")
        print("  python setup/build_db.py\n")
        sys.exit(1)

    # import subcommand — handle before parser (no book/chapter needed)
    if sys.argv[1].lower() == "import":
        importer.display(sys.argv[2:], DB_PATH)
        return

    parsed = parse_input(sys.argv[1:])

    if parsed["error"]:
        print(f"\n  Error: {parsed['error']}\n")
        sys.exit(1)

    mode = parsed["mode"]

    if mode == "lex":
        lex.display(parsed, DB_PATH)
    elif mode == "con":
        con.display(parsed, DB_PATH)
    elif mode == "cross":
        cross.display(parsed, DB_PATH)
    elif mode == "exeg":
        exeg.display(parsed, DB_PATH)
    else:
        passage.display(parsed, DB_PATH)


if __name__ == "__main__":
    main()
