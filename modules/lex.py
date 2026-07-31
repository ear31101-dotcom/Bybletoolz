import re
import sqlite3
from rich.console import Console
from rich.table import Table
from rich.rule import Rule
from rich.text import Text

console = Console()


def _has_custom_lexicon(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='custom_lexicon'")
    return cur.fetchone() is not None


def _custom_lookup(cur, number):
    """Return a custom lexicon row (9-column format) for a Strong's number, or None."""
    cur.execute(
        "SELECT number, language, word, transliteration, gloss, definition, root, NULL, NULL "
        "FROM custom_lexicon WHERE number=? LIMIT 1",
        (number,),
    )
    return cur.fetchone()


def display(parsed, db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    book        = parsed["book"]
    chapter     = parsed["chapter"]
    verse       = parsed["verse_start"]
    target_word = parsed["word"]

    # book/chapter scope with a Strong's number — definition + occurrence list
    if target_word and re.match(r'^[HhGg]\d+$', target_word) and verse is None:
        _show_scoped_strongs(cur, target_word, book, chapter)
        con.close()
        return

    # fetch verse text
    cur.execute(
        "SELECT text FROM verses WHERE book=? AND chapter=? AND verse=?",
        (book, chapter, verse),
    )
    row = cur.fetchone()
    if not row:
        console.print(f"[red]Verse not found: {book} {chapter}:{verse}[/red]")
        con.close()
        return

    verse_text = row[0]
    ref = f"{book} {chapter}:{verse}"

    console.print()
    console.rule(f"[bold cyan]{ref}  —  Lexicon[/bold cyan]", style="dim")
    console.print()
    console.print(f'  [dim]"{verse_text}"[/dim]')
    console.print()

    if target_word:
        _show_word(cur, target_word, ref, parsed["book"])
    else:
        _show_all_words(cur, book, chapter, verse, ref)

    con.close()


OT_BOOKS = {
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
    "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra",
    "Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Solomon",
    "Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi",
}


def _show_scoped_strongs(cur, word, book, chapter):
    """Show lexicon entry + scoped occurrence list for a direct Strong's number at book/chapter scope."""
    number = word.upper()

    if book and chapter:
        scope_label = f"{book} chapter {chapter}"
    elif book:
        scope_label = book
    else:
        scope_label = "Full Bible"

    console.print()
    console.rule(f"[bold cyan]{scope_label}  —  Lexicon  {number}[/bold cyan]", style="dim")
    console.print()

    # lexicon entry
    row = _custom_lookup(cur, number) if _has_custom_lexicon(cur) else None
    if not row:
        cur.execute(
            "SELECT number, language, word, transliteration, gloss, definition, root, rich_gloss, rich_definition "
            "FROM strongs WHERE number=?",
            (number,),
        )
        row = cur.fetchone()

    if not row:
        console.print(f"  [yellow]Strong's number '{number}' not found.[/yellow]")
        console.print()
        return

    _render_entry(row)

    # occurrence list
    if book and chapter:
        cur.execute(
            """
            SELECT vw.chapter, vw.verse, v.text
            FROM verse_words vw
            JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
            WHERE vw.strongs_number=? AND vw.book=? AND vw.chapter=?
              AND v.translation='KJV'
            ORDER BY vw.chapter, vw.verse
            """,
            (number, book, chapter),
        )
    elif book:
        cur.execute(
            """
            SELECT vw.chapter, vw.verse, v.text
            FROM verse_words vw
            JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
            WHERE vw.strongs_number=? AND vw.book=?
              AND v.translation='KJV'
            ORDER BY vw.chapter, vw.verse
            """,
            (number, book),
        )
    else:
        cur.execute(
            """
            SELECT vw.book || ' ' || vw.chapter, vw.verse, v.text
            FROM verse_words vw
            JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
            WHERE vw.strongs_number=?
              AND v.translation='KJV'
            ORDER BY vw.book, vw.chapter, vw.verse
            """,
            (number,),
        )

    occurrences = cur.fetchall()

    if not occurrences:
        console.print(f"  [dim]No occurrences of {number} found in {scope_label}.[/dim]")
        console.print()
        return

    console.rule(f"[dim]Occurrences in {scope_label}  ({len(occurrences)})[/dim]", style="dim")
    console.print()

    from rich.table import Table
    table = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    table.add_column("Ref",  style="yellow", min_width=20)
    table.add_column("Text", style="white")

    for ch_or_ref, verse_num, text in occurrences:
        if book and not chapter:
            ref_str = f"{book} {ch_or_ref}:{verse_num}"
        elif book and chapter:
            ref_str = f"{book} {ch_or_ref}:{verse_num}"
        else:
            ref_str = f"{ch_or_ref}:{verse_num}"
        table.add_row(ref_str, text)

    console.print(table)
    console.print()
    console.rule(style="dim")
    console.print()


def _show_word(cur, word, ref, book=""):
    # Direct Strong's number lookup: H7225 or G3056
    if re.match(r'^[HhGg]\d+$', word):
        number = word.upper()
        row = _custom_lookup(cur, number) if _has_custom_lexicon(cur) else None
        if not row:
            cur.execute(
                "SELECT number, language, word, transliteration, gloss, definition, root, rich_gloss, rich_definition FROM strongs WHERE number=?",
                (number,),
            )
            row = cur.fetchone()
        if row:
            _render_entry(row)
        else:
            console.print(f"[yellow]Strong's number '{number}' not found in lexicon.[/yellow]")
        return

    word_clean = word.lower().strip(".,;:!?\"'")
    stems = _word_stems(word_clean)

    # Parse verse ref to get candidate Strong's numbers from verse_words
    ref_parts = ref.split()
    # ref is like "Genesis 1:1" — book may be multi-word
    cv = ref_parts[-1]
    book_name = " ".join(ref_parts[:-1]) if len(ref_parts) > 2 else ref_parts[0]
    try:
        ch, v = cv.split(":")
        ch, v = int(ch), int(v)
    except ValueError:
        ch = v = None

    row = None

    if ch and v:
        # Get all Strong's entries for this verse, search gloss within that candidate set
        cur.execute(
            """
            SELECT s.number, s.language, s.word, s.transliteration, s.gloss, s.definition, s.root, s.rich_gloss, s.rich_definition
            FROM verse_words vw
            JOIN strongs s ON s.number = vw.strongs_number
            WHERE vw.book=? AND vw.chapter=? AND vw.verse=?
            ORDER BY vw.word_position
            """,
            (book_name, ch, v),
        )
        candidates = cur.fetchall()
        row = _best_match(candidates, stems)

    if not row:
        # Check custom lexicon by gloss before falling back to built-in
        if _has_custom_lexicon(cur):
            for stem in stems:
                cur.execute(
                    "SELECT number, language, word, transliteration, gloss, definition, root, NULL, NULL "
                    "FROM custom_lexicon WHERE LOWER(gloss) LIKE ? LIMIT 1",
                    (f"%{stem}%",),
                )
                row = cur.fetchone()
                if row:
                    break

    if not row:
        # Fallback: search all of Strong's, prefer correct testament language
        prefer_lang = "Hebrew" if book in OT_BOOKS else "Greek"
        row = _gloss_search(cur, stems, prefer_lang)
    if not row:
        row = _gloss_search(cur, stems, None)

    if not row:
        console.print(f"[yellow]No lexicon entry found for '{word}'.[/yellow]")
        console.print("[dim]Try using the root form (e.g. 'create' instead of 'created').[/dim]")
        return

    _render_entry(row)


def _show_all_words(cur, book, chapter, verse, ref):
    cur.execute(
        """
        SELECT vw.word_position, s.number, s.language, s.word, s.transliteration, s.gloss, s.root, s.rich_gloss
        FROM verse_words vw
        JOIN strongs s ON s.number = vw.strongs_number
        WHERE vw.book=? AND vw.chapter=? AND vw.verse=?
        ORDER BY vw.word_position
        """,
        (book, chapter, verse),
    )
    rows = cur.fetchall()

    if not rows:
        console.print("[yellow]No lexicon data mapped for this verse yet.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2), expand=False)
    table.add_column("#",        style="dim",    justify="right", min_width=2)
    table.add_column("Strong's", style="yellow", min_width=7)
    table.add_column("Lang",     style="dim",    min_width=6)
    table.add_column("Original", style="bold",   min_width=8)
    table.add_column("Translit.",style="cyan",   min_width=8)
    table.add_column("Gloss",    style="green")

    for pos, num, lang, orig, translit, gloss, root, rich_gloss in rows:
        display_gloss = rich_gloss or gloss
        short_gloss = (display_gloss or "").split(";")[0].strip()
        table.add_row(
            str(pos + 1),
            num or "",
            lang or "",
            orig or "",
            translit or "",
            short_gloss,
        )

    console.print(table)

    console.print()
    console.rule(style="dim")
    console.print()


def _best_match(candidates, stems):
    """Pick the candidate whose gloss or definition best matches one of the stems."""
    for stem in stems:
        for row in candidates:
            gloss = (row[4] or "").lower()
            defn  = (row[5] or "").lower()
            combined = gloss + " " + defn
            # prefer whole-word match first
            if re.search(r'\b' + re.escape(stem) + r'\b', combined):
                return row
        # fallback: substring match
        for row in candidates:
            combined = ((row[4] or "") + " " + (row[5] or "")).lower()
            if stem in combined:
                return row
    return None


def _word_stems(word):
    """Return a list of search stems from most to least specific."""
    stems = [word]
    for suffix in ("ed", "ing", "eth", "est", "s", "th", "d"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stems.append(word[: -len(suffix)])
    return list(dict.fromkeys(stems))  # deduplicate while preserving order


def _gloss_search(cur, stems, language):
    for stem in stems:
        # Prefer entries where the stem appears as a whole word (space-bounded or comma/semi-colon)
        # Order: exact word boundary match first, then shorter glosses (more specific)
        lang_clause = "AND language=?" if language else ""
        params_boundary = [f"% {stem} %", f"% {stem},%", f"% {stem};%", stem + " %"]
        params_boundary = [p for p in params_boundary]  # keep all

        if language:
            cur.execute(
                f"SELECT number, language, word, transliteration, gloss, definition, root, rich_gloss, rich_definition FROM strongs "
                f"WHERE (LOWER(gloss) LIKE ? OR LOWER(gloss) LIKE ? OR LOWER(gloss) LIKE ? OR LOWER(gloss) LIKE ?) "
                f"{lang_clause} ORDER BY LENGTH(gloss) LIMIT 1",
                (*params_boundary, language),
            )
        else:
            cur.execute(
                f"SELECT number, language, word, transliteration, gloss, definition, root, rich_gloss, rich_definition FROM strongs "
                f"WHERE (LOWER(gloss) LIKE ? OR LOWER(gloss) LIKE ? OR LOWER(gloss) LIKE ? OR LOWER(gloss) LIKE ?) "
                f"ORDER BY LENGTH(gloss) LIMIT 1",
                tuple(params_boundary),
            )
        row = cur.fetchone()
        if row:
            return row
    return None


def _render_entry(row):
    number, language, word, translit, gloss, definition, root, rich_gloss, rich_definition = row

    display_gloss = rich_gloss or gloss
    display_def   = rich_definition or definition

    console.print(f"  [yellow]{number}[/yellow]  [bold]{word}[/bold]  [cyan]{translit}[/cyan]  [dim]({language})[/dim]")
    console.print()
    if display_gloss:
        console.print(f"  [green]Gloss:[/green]  {display_gloss}")
    if root:
        console.print(f"  [green]Root:[/green]   {root}")
    if display_def:
        console.print()
        console.print(f"  [green]Definition:[/green]")
        console.print(f"  {display_def}", soft_wrap=True)

    console.print()
    console.rule(style="dim")
    console.print()
