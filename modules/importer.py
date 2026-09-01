"""
Custom data importer for Bybletoolz.

Supports:
  CSV/TSV — cross-references and lexicon entries
  e-Sword SQLite — .refi (cross-refs) and .dct (lexicons)

Usage via study.py:
  byble import xref myfile.csv "My Source"
  byble import lex  myfile.tsv "My Lexicon"
  byble import exeg myfile.cmtx "My Commentary"
  byble import list
  byble import remove "My Source"
"""
import sqlite3
import csv
import os
import re
from rich.console import Console
from rich.table import Table

console = Console()

OT_BOOKS = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
    "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra",
    "Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Solomon",
    "Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi",
]
NT_BOOKS = [
    "Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians",
    "Galatians","Ephesians","Philippians","Colossians","1 Thessalonians","2 Thessalonians",
    "1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James","1 Peter","2 Peter",
    "1 John","2 John","3 John","Jude","Revelation",
]
ALL_BOOKS = OT_BOOKS + NT_BOOKS


def _summarize_coverage(books):
    """Return a human-readable coverage string from a set of book names."""
    books = set(books)
    has_ot = books >= set(OT_BOOKS)
    has_nt = books >= set(NT_BOOKS)
    if has_ot and has_nt:
        return "Full Bible"
    if has_ot:
        return "OT only"
    if has_nt:
        return "NT only"
    # list books in canonical order, up to 5 then summarize
    ordered = [b for b in ALL_BOOKS if b in books]
    if len(ordered) <= 5:
        return ", ".join(ordered)
    return f"{', '.join(ordered[:4])} … ({len(ordered)} books)"

BOOK_NAME_MAP = {
    # e-Sword uses integer book numbers 1–66
    1: "Genesis", 2: "Exodus", 3: "Leviticus", 4: "Numbers", 5: "Deuteronomy",
    6: "Joshua", 7: "Judges", 8: "Ruth", 9: "1 Samuel", 10: "2 Samuel",
    11: "1 Kings", 12: "2 Kings", 13: "1 Chronicles", 14: "2 Chronicles",
    15: "Ezra", 16: "Nehemiah", 17: "Esther", 18: "Job", 19: "Psalms",
    20: "Proverbs", 21: "Ecclesiastes", 22: "Song of Solomon", 23: "Isaiah",
    24: "Jeremiah", 25: "Lamentations", 26: "Ezekiel", 27: "Daniel",
    28: "Hosea", 29: "Joel", 30: "Amos", 31: "Obadiah", 32: "Jonah",
    33: "Micah", 34: "Nahum", 35: "Habakkuk", 36: "Zephaniah", 37: "Haggai",
    38: "Zechariah", 39: "Malachi", 40: "Matthew", 41: "Mark", 42: "Luke",
    43: "John", 44: "Acts", 45: "Romans", 46: "1 Corinthians",
    47: "2 Corinthians", 48: "Galatians", 49: "Ephesians", 50: "Philippians",
    51: "Colossians", 52: "1 Thessalonians", 53: "2 Thessalonians",
    54: "1 Timothy", 55: "2 Timothy", 56: "Titus", 57: "Philemon",
    58: "Hebrews", 59: "James", 60: "1 Peter", 61: "2 Peter",
    62: "1 John", 63: "2 John", 64: "3 John", 65: "Jude", 66: "Revelation",
}


def _ensure_custom_tables(cur):
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS custom_xrefs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            from_book   TEXT NOT NULL,
            from_chapter INTEGER NOT NULL,
            from_verse  INTEGER NOT NULL,
            to_book     TEXT NOT NULL,
            to_chapter  INTEGER NOT NULL,
            to_verse    INTEGER NOT NULL,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS custom_lexicon (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            number      TEXT NOT NULL,
            language    TEXT,
            word        TEXT,
            transliteration TEXT,
            gloss       TEXT,
            definition  TEXT,
            root        TEXT,
            UNIQUE(source_name, number)
        );

        CREATE TABLE IF NOT EXISTS commentary (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name   TEXT NOT NULL,
            book          TEXT NOT NULL,
            chapter       INTEGER NOT NULL,
            verse         INTEGER NOT NULL,
            chapter_end   INTEGER NOT NULL DEFAULT 0,
            verse_end     INTEGER NOT NULL DEFAULT 0,
            text          TEXT NOT NULL,
            article_title TEXT
        );

        CREATE TABLE IF NOT EXISTS commentary_sources (
            source_name   TEXT PRIMARY KEY,
            data_type     TEXT NOT NULL,
            verse_count   INTEGER NOT NULL DEFAULT 0,
            books_covered TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_cxref_from
            ON custom_xrefs (from_book, from_chapter, from_verse);
        CREATE INDEX IF NOT EXISTS idx_clex_number
            ON custom_lexicon (number);
        CREATE INDEX IF NOT EXISTS idx_commentary_ref
            ON commentary (book, chapter, verse, chapter_end, verse_end);
    """)
    # migrate existing databases that predate verse_end / chapter_end columns
    cur.execute("PRAGMA table_info(commentary)")
    cols = {row[1] for row in cur.fetchall()}
    if "verse_end" not in cols:
        cur.execute("ALTER TABLE commentary ADD COLUMN verse_end INTEGER NOT NULL DEFAULT 0")
        cur.execute("UPDATE commentary SET verse_end = verse WHERE verse_end = 0")
    if "chapter_end" not in cols:
        cur.execute("ALTER TABLE commentary ADD COLUMN chapter_end INTEGER NOT NULL DEFAULT 0")
        cur.execute("UPDATE commentary SET chapter_end = chapter WHERE chapter_end = 0")
    if "article_title" not in cols:
        cur.execute("ALTER TABLE commentary ADD COLUMN article_title TEXT")


def display(args, db_path):
    if not args:
        _usage()
        return

    sub = args[0].lower()

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    _ensure_custom_tables(cur)
    con.commit()

    if sub == "list":
        _cmd_list(cur)
    elif sub == "remove":
        name = args[1] if len(args) > 1 else None
        _cmd_remove(cur, con, name)
    elif sub in ("xref", "lex", "exeg"):
        path = args[1] if len(args) > 1 else None
        name = args[2] if len(args) > 2 else (os.path.basename(path) if path else "unnamed")
        if not path:
            console.print(f"[red]Provide a file path. Example: byble import {sub} myfile.csv \"My Source\"[/red]")
        elif not os.path.exists(path):
            console.print(f"[red]File not found: {path}[/red]")
        else:
            if sub == "xref":
                _import_xref(cur, con, path, name)
            elif sub == "lex":
                _import_lex(cur, con, path, name)
            else:
                _import_exeg(cur, con, path, name)
    else:
        _usage()

    con.close()


def _usage():
    console.print()
    console.print("  [bold]byble import[/bold] — custom data import")
    console.print()
    console.print("  [yellow]byble import xref   <file> [\"Source Name\"][/yellow]   Import cross-references (CSV/TSV or e-Sword .refi)")
    console.print("  [yellow]byble import lex    <file> [\"Source Name\"][/yellow]   Import lexicon entries (CSV/TSV or e-Sword .dct)")
    console.print("  [yellow]byble import exeg   <file> [\"Source Name\"][/yellow]   Import commentary (CSV/TSV or e-Sword .cmtx)")
    console.print("  [yellow]byble import list[/yellow]                            List all imported sources")
    console.print("  [yellow]byble import remove \"Source Name\"[/yellow]            Remove an imported source")
    console.print()


def _cmd_list(cur):
    console.print()
    console.rule("[bold cyan]Imported Sources[/bold cyan]", style="dim")
    console.print()

    cur.execute("SELECT source_name, COUNT(*) FROM custom_xrefs GROUP BY source_name")
    xref_rows = cur.fetchall()

    cur.execute("SELECT source_name, COUNT(*) FROM custom_lexicon GROUP BY source_name")
    lex_rows = cur.fetchall()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commentary_sources'")
    has_commentary = cur.fetchone() is not None
    com_rows = []
    if has_commentary:
        cur.execute(
            "SELECT source_name, verse_count, books_covered FROM commentary_sources ORDER BY source_name"
        )
        com_rows = cur.fetchall()

    if not xref_rows and not lex_rows and not com_rows:
        console.print("  [dim]No custom sources imported yet.[/dim]")
        console.print()
        return

    if xref_rows:
        console.print("  [green]Cross-reference sources:[/green]")
        for name, count in xref_rows:
            console.print(f"    [yellow]{name}[/yellow]  —  {count:,} references")
        console.print()

    if lex_rows:
        console.print("  [green]Lexicon sources:[/green]")
        for name, count in lex_rows:
            console.print(f"    [yellow]{name}[/yellow]  —  {count:,} entries")
        console.print()

    if com_rows:
        console.print("  [green]Commentary sources:[/green]")
        for name, count, coverage in com_rows:
            console.print(f"    [yellow]{name}[/yellow]  —  {count:,} notes  [dim]({coverage})[/dim]")
        console.print()

    console.rule(style="dim")
    console.print()


def _cmd_remove(cur, con, name):
    if not name:
        console.print("[red]Provide a source name. Example: byble import remove \"My Source\"[/red]")
        return

    cur.execute("DELETE FROM custom_xrefs WHERE source_name=?", (name,))
    xref_count = cur.rowcount
    cur.execute("DELETE FROM custom_lexicon WHERE source_name=?", (name,))
    lex_count = cur.rowcount

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commentary'")
    com_count = 0
    if cur.fetchone():
        cur.execute("DELETE FROM commentary WHERE source_name=?", (name,))
        com_count = cur.rowcount
        cur.execute("DELETE FROM commentary_sources WHERE source_name=?", (name,))

    con.commit()

    if xref_count + lex_count + com_count == 0:
        console.print(f"[yellow]No source named \"{name}\" found.[/yellow]")
    else:
        parts = []
        if xref_count: parts.append(f"{xref_count:,} cross-refs")
        if lex_count:  parts.append(f"{lex_count:,} lexicon entries")
        if com_count:  parts.append(f"{com_count:,} commentary notes")
        console.print(f"  Removed [yellow]\"{name}\"[/yellow]: {', '.join(parts)}.")


# ── CSV/TSV helpers ───────────────────────────────────────────────────────────

def _detect_delimiter(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        sample = f.read(2048)
    tabs = sample.count("\t")
    commas = sample.count(",")
    return "\t" if tabs >= commas else ","


def _import_xref(cur, con, path, name):
    ext = os.path.splitext(path)[1].lower()

    if ext in (".db", ".sqlite", ".sqlite3", ".refi"):
        rows = _read_esword_xref(path)
        fmt = "e-Sword"
    else:
        rows = _read_csv_xref(path)
        fmt = "CSV/TSV"

    if rows is None:
        return

    cur.execute("DELETE FROM custom_xrefs WHERE source_name=?", (name,))
    cur.executemany(
        "INSERT INTO custom_xrefs (source_name, from_book, from_chapter, from_verse, to_book, to_chapter, to_verse, notes) VALUES (?,?,?,?,?,?,?,?)",
        [(name, r[0], r[1], r[2], r[3], r[4], r[5], r[6] if len(r) > 6 else None) for r in rows],
    )
    con.commit()
    console.print(f"  Imported [green]{len(rows):,}[/green] cross-references from {fmt} as [yellow]\"{name}\"[/yellow].")


def _import_lex(cur, con, path, name):
    ext = os.path.splitext(path)[1].lower()

    if ext in (".db", ".sqlite", ".sqlite3", ".dct"):
        rows = _read_esword_lex(path)
        fmt = "e-Sword"
    else:
        rows = _read_csv_lex(path)
        fmt = "CSV/TSV"

    if rows is None:
        return

    cur.execute("DELETE FROM custom_lexicon WHERE source_name=?", (name,))
    cur.executemany(
        """INSERT OR REPLACE INTO custom_lexicon
           (source_name, number, language, word, transliteration, gloss, definition, root)
           VALUES (?,?,?,?,?,?,?,?)""",
        [(name, r[0], r[1], r[2], r[3], r[4], r[5], r[6] if len(r) > 6 else None) for r in rows],
    )
    con.commit()
    console.print(f"  Imported [green]{len(rows):,}[/green] lexicon entries from {fmt} as [yellow]\"{name}\"[/yellow].")


def _read_csv_xref(path):
    """
    Expected columns (header row required):
      from_book, from_chapter, from_verse, to_book, to_chapter, to_verse[, notes]
    """
    delim = _detect_delimiter(path)
    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=delim)
            headers = [h.lower().strip() for h in (reader.fieldnames or [])]
            required = {"from_book", "from_chapter", "from_verse", "to_book", "to_chapter", "to_verse"}
            missing = required - set(headers)
            if missing:
                console.print(f"[red]Missing columns: {', '.join(missing)}[/red]")
                console.print("[dim]Required: from_book, from_chapter, from_verse, to_book, to_chapter, to_verse[/dim]")
                return None
            for row in reader:
                r = {k.lower().strip(): v for k, v in row.items()}
                try:
                    rows.append((
                        r["from_book"].strip(),
                        int(r["from_chapter"]),
                        int(r["from_verse"]),
                        r["to_book"].strip(),
                        int(r["to_chapter"]),
                        int(r["to_verse"]),
                        r.get("notes", "").strip() or None,
                    ))
                except (ValueError, KeyError):
                    continue
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        return None
    return rows


def _read_csv_lex(path):
    """
    Expected columns (header row required):
      number, gloss, definition[, language, word, transliteration, root]
    number should be Strong's format: H1, G3056, etc.
    """
    delim = _detect_delimiter(path)
    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=delim)
            headers = [h.lower().strip() for h in (reader.fieldnames or [])]
            required = {"number", "gloss", "definition"}
            missing = required - set(headers)
            if missing:
                console.print(f"[red]Missing columns: {', '.join(missing)}[/red]")
                console.print("[dim]Required: number, gloss, definition  |  Optional: language, word, transliteration, root[/dim]")
                return None
            for row in reader:
                r = {k.lower().strip(): v for k, v in row.items()}
                number = r.get("number", "").strip().upper()
                if not number:
                    continue
                lang = r.get("language", "").strip()
                if not lang:
                    lang = "Hebrew" if number.startswith("H") else "Greek" if number.startswith("G") else ""
                rows.append((
                    number,
                    lang,
                    r.get("word", "").strip() or None,
                    r.get("transliteration", "").strip() or None,
                    r.get("gloss", "").strip() or None,
                    r.get("definition", "").strip() or None,
                    r.get("root", "").strip() or None,
                ))
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        return None
    return rows


# ── XLSX helpers ─────────────────────────────────────────────────────────────

def _read_xlsx_commentary(path):
    """
    Supports two XLSX layouts:

    Standard layout — column headers include book, chapter, verse, text
    (verse_end optional):
        book | chapter | verse | verse_end | text

    Embedded-verse layout — column headers include section/chapter/text
    with verse refs at the start of each text cell (e.g. SDA Bible Commentary):
        record_id | ... | row_type | section | chapter | text
        paragraphs with text like "1-3 (Ps. 33:6). Note text..." or
        continuation paragraphs with no leading verse ref.

    Continuation paragraphs (no verse ref) are merged into the preceding note.
    """
    try:
        import openpyxl
    except ImportError:
        console.print("[red]openpyxl is required for XLSX import.[/red]")
        console.print("[dim]Install it: pip install openpyxl[/dim]")
        return None

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        raw = list(ws.iter_rows(values_only=True))
    except Exception as e:
        console.print(f"[red]Error reading XLSX file: {e}[/red]")
        return None

    if not raw:
        console.print("[red]XLSX file is empty.[/red]")
        return None

    headers = [str(h).lower().strip() if h is not None else "" for h in raw[0]]

    # ── standard layout ──
    if "book" in headers and "chapter" in headers and "verse" in headers and "text" in headers:
        bi  = headers.index("book")
        ci  = headers.index("chapter")
        vi  = headers.index("verse")
        vei = headers.index("verse_end") if "verse_end" in headers else None
        ti  = headers.index("text")
        rows = []
        for row in raw[1:]:
            try:
                book  = str(row[bi]).strip()
                ch    = int(row[ci])
                vs    = int(row[vi])
                ve    = int(row[vei]) if vei is not None and row[vei] else vs
                text  = str(row[ti]).strip()
                if book and text:
                    rows.append((book, ch, vs, ch, ve, text))
            except (ValueError, TypeError):
                continue
        return rows

    # ── Advanced Structured layout ──
    if "chapter_start" in headers and "book" in headers and "text" in headers:
        data = []
        for row in raw[1:]:
            data.append({headers[i]: (str(row[i]).strip() if row[i] is not None else "") for i in range(len(headers))})
        return _parse_structured_rows(data)  # returns (verse_rows, article_rows)

    # ── embedded-verse layout (SDA-style) ──
    if "section" in headers and "chapter" in headers and "text" in headers:
        si  = headers.index("section")
        ci  = headers.index("chapter")
        ti  = headers.index("text")
        rti = headers.index("row_type") if "row_type" in headers else None
        return _parse_embedded_verse_xlsx(raw[1:], si, ci, ti, rti)

    console.print("[red]XLSX format not recognised.[/red]")
    console.print("[dim]Expected columns: book/chapter/verse/text  or  section/chapter/text[/dim]")
    return None


def _parse_embedded_verse_xlsx(data_rows, si, ci, ti, rti):
    """
    Parse SDA-style XLSX where verse refs are embedded at the start of text cells.
    Continuation paragraphs (no leading verse ref) are appended to the current note.

    Verse ref patterns recognised:
      "1"           single verse
      "1-3"         range
      "1–3"         range (em-dash)
      "16, 17"      comma-separated (treated as range: first to last)
      "1-3 (..."    ref followed by cross-reference in parens — ref stripped
    """
    rows = []
    current_book    = None
    current_chapter = None
    current_verse   = None
    current_end     = None
    current_text    = None

    def _flush():
        if current_book and current_verse is not None and current_text:
            rows.append((current_book, current_chapter, current_verse, current_chapter, current_end, current_text.strip()))

    for row in data_rows:
        try:
            rt   = str(row[rti]).strip().lower() if rti is not None and row[rti] else ""
            book = str(row[si]).strip() if row[si] else None
            ch   = int(row[ci]) if row[ci] else None
            text = str(row[ti]).strip() if row[ti] else None
        except (ValueError, TypeError):
            continue

        # skip headings and empty rows
        if not text or (rti is not None and rt in ("section_heading", "chapter_heading")):
            continue
        if not book or not ch:
            continue

        # try to parse a leading verse ref
        m = re.match(
            r'^((?:\d+\s*[-–]\s*\d+|\d+(?:\s*,\s*\d+)+|\d+))\s*(?:\(|\.|\s|$)',
            text
        )
        if m:
            ref_str = m.group(1).strip()
            nums = [int(n) for n in re.findall(r'\d+', ref_str)]
            v_start = nums[0]
            v_end   = nums[-1]  # last number covers range or comma list
            _flush()
            current_book    = book
            current_chapter = ch
            current_verse   = v_start
            current_end     = v_end
            current_text    = text
        else:
            # continuation — append to current note if same book/chapter
            if current_book == book and current_chapter == ch and current_text is not None:
                current_text += "\n\n" + text
            else:
                # new book/chapter with no verse ref — skip (can't anchor it)
                pass

    _flush()
    return rows


def _parse_verse_int(raw):
    """Convert a verse string like '4b' or '12' to an integer, stripping letter suffixes."""
    if not raw:
        return None
    m = re.match(r'(\d+)', str(raw).strip())
    return int(m.group(1)) if m else None


def _parse_structured_rows(dict_rows):
    """
    Shared parser for Advanced Structured commentary rows (CSV or XLSX).
    Expects each row to be a dict with lowercase keys including:
      book, chapter_start, verse_start, chapter_end, verse_end, assignment_source, text

    Returns a tuple: (verse_rows, article_rows)
      verse_rows   — list of (book, ch_s, vs, ch_e, ve, text) for standard notes
      article_rows — list of (title, text) for assignment_source='article' rows
                     where book='Article' and chapter_start holds the title

    Article rows in the CSV:
      book,chapter_start,...,assignment_source,text
      Article,My Title,,,,article,"Paragraph one..."
      Article,My Title,,,,article,"Paragraph two..."

    Only rows with assignment_source in (explicit_scope, carried_scope, book_introduction,
    article) are imported. Paragraphs sharing the same scope/title are merged.
    """
    rows = []
    article_rows = []
    current_key  = None
    current_text = []
    current_article_title = None
    current_article_text  = []

    def _flush():
        if current_key and current_text:
            book, ch_s, vs, ch_e, ve = current_key
            # strip leading verse-reference prefix from the first paragraph
            # e.g. "2:1-34. Camps and Leaders..." → "Camps and Leaders..."
            first = re.sub(
                r'^\d+\s*:\s*\d+\s*[-–]\s*\d+\s*:\s*\d+\s*[.\s]*',
                '', current_text[0]
            ).strip()
            first = re.sub(
                r'^\d+\s*:\s*\d+\s*[-–]\s*\d+\s*[.\s]*',
                '', first
            ).strip()
            paragraphs = ([first] if first else []) + current_text[1:]
            merged = "\n\n".join(paragraphs).strip()
            if merged:
                rows.append((book, ch_s, vs, ch_e, ve, merged))

    def _flush_article():
        if current_article_title and current_article_text:
            merged = "\n\n".join(current_article_text).strip()
            if merged:
                article_rows.append((current_article_title, merged))

    for r in dict_rows:
        src = r.get("assignment_source", "").strip()
        if src not in ("explicit_scope", "carried_scope", "book_introduction", "article"):
            _flush()
            _flush_article()
            current_key           = None
            current_text          = []
            current_article_title = None
            current_article_text  = []
            continue

        # ── article rows ──────────────────────────────────────────────────────
        if src == "article":
            book_col = r.get("book", "").strip()
            if book_col.lower() != "article":
                continue  # malformed — book column must be "Article"
            title = r.get("chapter_start", "").strip()
            text  = r.get("text", "").strip()
            if not title or not text:
                continue
            _flush()
            current_key  = None
            current_text = []
            if title != current_article_title:
                _flush_article()
                current_article_title = title
                current_article_text  = [text]
            else:
                current_article_text.append(text)
            continue

        # book introductions stored at chapter=0, verse=0 (book-level sentinel)
        if src == "book_introduction":
            book = r.get("book", "").strip()
            text = r.get("text", "").strip()
            if not book or not text:
                continue
            # skip bare title/heading lines ("GENESIS", "INTRODUCTION")
            if text.isupper() and len(text.split()) <= 3:
                continue
            # skip PDF sidebar/column artifacts — four signatures:
            #   1. ends with a hyphen (narrow-column line wrap, e.g. "veg-")
            #   2. ≤ 6 words with no terminal punctuation (partial headings
            #      like "Days of", "Chronicles the", "of")
            #   3. short line (< 110 chars) that doesn't end with sentence-
            #      terminal punctuation — narrow sidebar columns produce lines
            #      of ~35–90 chars that break mid-sentence
            #   4. starts with lowercase — either a sidebar continuation line
            #      or a sidebar-tail merged with main text; in the latter case
            #      strip the sidebar prefix up to the first ". [A-Z]" boundary
            #      and keep the remainder only if it is substantive (≥ 30 chars)
            if text.endswith("-"):
                continue
            words = text.split()
            if len(words) <= 6 and not re.search(r'[.!?:;,)]$', text):
                continue
            if len(text) < 110 and not re.search(r'[.!?:"]$', text):
                continue
            if text and text[0].islower():
                m = re.search(r'\.\s+([A-Z])', text)
                if m:
                    remainder = text[m.start(1):].strip()
                    # remainder must be substantive AND end with terminal punct
                    if len(remainder) >= 30 and re.search(r'[.!?"]$', remainder):
                        text = remainder
                    else:
                        continue
                else:
                    continue
            key = (book, 0, 0, 0, 0)
            if key != current_key:
                _flush()
                current_key  = key
                current_text = [text]
            else:
                current_text.append(text)
            continue

        book     = r.get("book", "").strip()
        ch_s     = _parse_verse_int(r.get("chapter_start", ""))
        vs       = _parse_verse_int(r.get("verse_start", ""))
        ch_e_raw = r.get("chapter_end", "").strip()
        ve_raw   = r.get("verse_end", "").strip()
        ch_e     = _parse_verse_int(ch_e_raw) if ch_e_raw else ch_s
        ve       = _parse_verse_int(ve_raw)   if ve_raw   else vs
        text     = r.get("text", "").strip()

        if not book or ch_s is None or vs is None or not text:
            continue

        # skip standalone verse-reference labels (e.g. "1:1-10:10") — they
        # duplicate the scope label already shown by the display layer
        if re.match(r'^\d+:\d+\s*[-–]\s*\d+:\d+$', text) or re.match(r'^\d+:\d+$', text):
            continue

        key = (book, ch_s, vs, ch_e, ve)
        if key != current_key:
            _flush()
            current_key  = key
            current_text = [text]
        else:
            current_text.append(text)

    _flush()
    _flush_article()
    return rows, article_rows


def _read_structured_csv(path):
    """Parse an Advanced Structured commentary CSV.
    Returns (verse_rows, article_rows) or (None, None) on error."""
    delim = _detect_delimiter(path)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=delim)
            dict_rows = [{k.lower().strip(): v for k, v in row.items()} for row in reader]
    except Exception as e:
        console.print(f"[red]Error reading structured CSV: {e}[/red]")
        return None, None
    return _parse_structured_rows(dict_rows)


# ── e-Sword helpers ───────────────────────────────────────────────────────────

def _read_esword_xref(path):
    """
    e-Sword .refi files are SQLite with a CrossReference table.
    Columns: Book, Chapter, Verse, CrossBook, CrossChapter, CrossVerse
    Book numbers are 1-based integers (1=Genesis … 66=Revelation).
    """
    rows = []
    try:
        econ = sqlite3.connect(path)
        ecur = econ.cursor()
        ecur.execute("SELECT Book, Chapter, Verse, CrossBook, CrossChapter, CrossVerse FROM CrossReference")
        for fb, fc, fv, tb, tc, tv in ecur.fetchall():
            from_book = BOOK_NAME_MAP.get(int(fb))
            to_book   = BOOK_NAME_MAP.get(int(tb))
            if from_book and to_book:
                rows.append((from_book, int(fc), int(fv), to_book, int(tc), int(tv), None))
        econ.close()
    except Exception as e:
        console.print(f"[red]Error reading e-Sword file: {e}[/red]")
        return None
    return rows


def _read_esword_lex(path):
    """
    e-Sword .dct files are SQLite with a Dictionary table.
    Columns: Topic (e.g. H0001 or G0001), Definition (RTF/HTML text).
    """
    rows = []
    try:
        econ = sqlite3.connect(path)
        ecur = econ.cursor()
        ecur.execute("SELECT Topic, Definition FROM Dictionary")
        for topic, defn in ecur.fetchall():
            topic = (topic or "").strip().upper()
            # Normalize H0001 → H1, G0001 → G1
            m = re.match(r'^([HG])(\d+)', topic)
            if not m:
                continue
            prefix, digits = m.group(1), m.group(2)
            number = f"{prefix}{int(digits)}"
            lang = "Hebrew" if prefix == "H" else "Greek"
            clean_def = _strip_rtf_html(defn or "")
            rows.append((number, lang, None, None, None, clean_def, None))
        econ.close()
    except Exception as e:
        console.print(f"[red]Error reading e-Sword file: {e}[/red]")
        return None
    return rows


def _import_exeg(cur, con, path, name):
    ext = os.path.splitext(path)[1].lower()
    article_rows = []

    if ext in (".db", ".sqlite", ".sqlite3", ".cmtx"):
        rows = _read_esword_commentary(path)
        fmt = "e-Sword"
    elif ext in (".xlsx", ".xls"):
        result = _read_xlsx_commentary(path)
        if isinstance(result, tuple):
            rows, article_rows = result
        else:
            rows = result
        fmt = "XLSX"
    else:
        # detect Advanced Structured CSV by presence of chapter_start column
        delim = _detect_delimiter(path)
        with open(path, "r", encoding="utf-8-sig") as f:
            first_line = f.readline()
        headers = {h.lower().strip() for h in first_line.split(delim)}
        if "chapter_start" in headers:
            rows, article_rows = _read_structured_csv(path)
            fmt = "Structured CSV"
        else:
            rows = _read_csv_commentary(path)
            fmt = "CSV/TSV"

    if rows is None:
        return

    cur.execute("DELETE FROM commentary WHERE source_name=?", (name,))
    cur.execute("DELETE FROM commentary_sources WHERE source_name=?", (name,))

    # insert verse/book-introduction notes
    cur.executemany(
        "INSERT INTO commentary (source_name, book, chapter, verse, chapter_end, verse_end, text) VALUES (?,?,?,?,?,?,?)",
        [(name, r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows],
    )

    # insert article rows — stored with book='Article', chapter=-1, verse=-1
    if article_rows:
        cur.executemany(
            "INSERT INTO commentary (source_name, book, chapter, verse, chapter_end, verse_end, text, article_title) VALUES (?,?,?,?,?,?,?,?)",
            [(name, "Article", -1, -1, -1, -1, text, title) for title, text in article_rows],
        )

    # build coverage summary — exclude the sentinel "Article" book
    books_in_source = sorted(
        {r[0] for r in rows if r[0] in ALL_BOOKS},
        key=lambda b: ALL_BOOKS.index(b),
    )
    coverage = _summarize_coverage(books_in_source)
    if article_rows:
        coverage = (coverage + f", {len(article_rows)} article(s)") if coverage else f"{len(article_rows)} article(s)"

    cur.execute(
        "INSERT OR REPLACE INTO commentary_sources (source_name, data_type, verse_count, books_covered) VALUES (?,?,?,?)",
        (name, fmt, len(rows), coverage),
    )

    con.commit()
    console.print(f"  Imported [green]{len(rows):,}[/green] commentary notes from {fmt} as [yellow]\"{name}\"[/yellow].")
    if article_rows:
        console.print(f"  Imported [green]{len(article_rows):,}[/green] article(s).")
    console.print(f"  Coverage: [dim]{coverage}[/dim]")


def _read_csv_commentary(path):
    """
    Expected columns (header row required):
      book, chapter, verse, text[, verse_end]
    verse_end is optional — omit or leave blank for single-verse notes.
    """
    delim = _detect_delimiter(path)
    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=delim)
            headers = [h.lower().strip() for h in (reader.fieldnames or [])]
            required = {"book", "chapter", "verse", "text"}
            missing = required - set(headers)
            if missing:
                console.print(f"[red]Missing columns: {', '.join(missing)}[/red]")
                console.print("[dim]Required: book, chapter, verse, text  |  Optional: verse_end[/dim]")
                return None
            for row in reader:
                r = {k.lower().strip(): v for k, v in row.items()}
                try:
                    text = r.get("text", "").strip()
                    if not text:
                        continue
                    v_start = int(r["verse"])
                    ve_raw = r.get("verse_end", "").strip()
                    v_end = int(ve_raw) if ve_raw else v_start
                    ch = int(r["chapter"])
                    rows.append((
                        r["book"].strip(),
                        ch, v_start,
                        ch, v_end,
                        text,
                    ))
                except (ValueError, KeyError):
                    continue
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        return None
    return rows


def _read_esword_commentary(path):
    """
    e-Sword .cmtx files are SQLite with a Commentary table.
    Columns: Book (int 1-66), Chapter, Verse, Marker, CommentaryText
    Marker may encode a verse range like "1-5" or "3,4,5".
    Text is often RTF or HTML mixed.
    """
    rows = []
    try:
        econ = sqlite3.connect(path)
        ecur = econ.cursor()
        ecur.execute("SELECT Book, Chapter, Verse, Marker, CommentaryText FROM Commentary")
        for book_num, chapter, verse, marker, text in ecur.fetchall():
            book = BOOK_NAME_MAP.get(int(book_num))
            if not book or not text:
                continue
            clean = _strip_rtf_html(text)
            if not clean:
                continue
            v_start = int(verse)
            v_end = _parse_marker_end(marker, v_start)
            ch = int(chapter)
            rows.append((book, ch, v_start, ch, v_end, clean))
        econ.close()
    except Exception as e:
        console.print(f"[red]Error reading e-Sword file: {e}[/red]")
        return None
    return rows


def _parse_marker_end(marker, v_start):
    """Extract the last verse number from an e-Sword marker string, or return v_start."""
    if not marker:
        return v_start
    marker = str(marker).strip()
    # range like "3-7" or "3–7"
    m = re.match(r'^\d+\s*[-–]\s*(\d+)$', marker)
    if m:
        return int(m.group(1))
    # comma-separated like "3,4,5"
    parts = re.findall(r'\d+', marker)
    if parts:
        return int(parts[-1])
    return v_start


def _strip_rtf_html(text):
    """Strip RTF codes and HTML tags from e-Sword definition text."""
    # RTF: strip \word and {groups}
    text = re.sub(r'\\[a-zA-Z]+\d*\s?', ' ', text)
    text = re.sub(r'[{}]', '', text)
    # HTML tags
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
