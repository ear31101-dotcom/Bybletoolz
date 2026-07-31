import sqlite3
from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

PAGE_SIZE = 20


def display(parsed, db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    book    = parsed["book"]
    chapter = parsed["chapter"]
    verse   = parsed["verse_start"]
    word    = parsed["word"]

    # build scope label and header ref
    if book and chapter and verse:
        ref = f"{book} {chapter}:{verse}"
        scope_label = f"verse {ref}"
    elif book and chapter:
        ref = f"{book} {chapter}"
        scope_label = f"{book} chapter {chapter}"
    elif book:
        ref = book
        scope_label = book
    else:
        ref = "Full Bible"
        scope_label = "full Bible"

    # fetch verse text for verse-scope (used as context header)
    verse_text = None
    if verse:
        cur.execute(
            "SELECT text FROM verses WHERE book=? AND chapter=? AND verse=?",
            (book, chapter, verse),
        )
        row = cur.fetchone()
        if not row:
            console.print(f"[red]Verse not found: {ref}[/red]")
            con.close()
            return
        verse_text = row[0]

    if not word:
        console.print()
        console.rule(f"[bold cyan]{ref}  —  Concordance[/bold cyan]", style="dim")
        console.print()
        if verse_text:
            console.print(f'  [dim]"{verse_text}"[/dim]')
            console.print()
        word = console.input("  [bold]Enter word or Strong's number to search:[/bold] ").strip()
        if not word:
            console.print("[red]No word entered. Exiting.[/red]")
            con.close()
            return

    word_clean = word.lower().strip(".,;:!?\"'")

    # resolve Strong's number
    strongs_number = _resolve_strongs(cur, word_clean, book, chapter, verse)

    console.print()
    console.rule(f"[bold cyan]{ref}  —  Concordance[/bold cyan]", style="dim")
    console.print()
    if verse_text:
        console.print(f'  [dim]"{verse_text}"[/dim]')
        console.print()

    if strongs_number:
        cur.execute(
            "SELECT language, word, transliteration, gloss FROM strongs WHERE number=?",
            (strongs_number,),
        )
        lex = cur.fetchone()
        if lex:
            lang, orig, translit, gloss = lex
            console.print(
                f"  [blue]Search:[/blue] [yellow]{word}[/yellow]  "
                f"[dim]({strongs_number} · {orig} · {translit} — \"{gloss}\")[/dim]  "
                f"[dim]in {scope_label}[/dim]"
            )

        # build scoped query
        if book and chapter and verse:
            cur.execute(
                """
                SELECT vw.book, vw.chapter, vw.verse, v.text
                FROM verse_words vw
                JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
                WHERE vw.strongs_number=? AND vw.book=? AND vw.chapter=? AND vw.verse=?
                ORDER BY vw.book, vw.chapter, vw.verse
                """,
                (strongs_number, book, chapter, verse),
            )
        elif book and chapter:
            cur.execute(
                """
                SELECT vw.book, vw.chapter, vw.verse, v.text
                FROM verse_words vw
                JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
                WHERE vw.strongs_number=? AND vw.book=? AND vw.chapter=?
                ORDER BY vw.chapter, vw.verse
                """,
                (strongs_number, book, chapter),
            )
        elif book:
            cur.execute(
                """
                SELECT vw.book, vw.chapter, vw.verse, v.text
                FROM verse_words vw
                JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
                WHERE vw.strongs_number=? AND vw.book=?
                ORDER BY vw.chapter, vw.verse
                """,
                (strongs_number, book),
            )
        else:
            cur.execute(
                """
                SELECT vw.book, vw.chapter, vw.verse, v.text
                FROM verse_words vw
                JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
                WHERE vw.strongs_number=?
                ORDER BY vw.book, vw.chapter, vw.verse
                """,
                (strongs_number,),
            )
    else:
        # plain text search fallback — scope to book/chapter if given
        console.print(
            f"  [blue]Search:[/blue] [yellow]{word}[/yellow]  "
            f"[dim](text search — no Strong's mapping found)  in {scope_label}[/dim]"
        )
        if book and chapter:
            cur.execute(
                "SELECT book, chapter, verse, text FROM verses "
                "WHERE LOWER(text) LIKE ? AND book=? AND chapter=? ORDER BY verse",
                (f"% {word_clean} %", book, chapter),
            )
        elif book:
            cur.execute(
                "SELECT book, chapter, verse, text FROM verses "
                "WHERE LOWER(text) LIKE ? AND book=? ORDER BY chapter, verse",
                (f"% {word_clean} %", book),
            )
        else:
            cur.execute(
                "SELECT book, chapter, verse, text FROM verses "
                "WHERE LOWER(text) LIKE ? ORDER BY book, chapter, verse",
                (f"% {word_clean} %",),
            )

    results = cur.fetchall()
    total = len(results)

    console.print(f"  [blue]Total occurrences:[/blue] [green]{total} verses[/green]")
    console.print()

    if not results:
        con.close()
        return

    _paginate(results, word_clean, total)
    _book_frequency(results)

    con.close()


OT_BOOKS = {
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
    "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra",
    "Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Solomon",
    "Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi",
}


def _stems(word):
    """Return search stems from most to least specific."""
    stems = [word]
    for suffix in ("ed", "ing", "eth", "est", "s", "th", "d", "e"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stems.append(word[: -len(suffix)])
    return list(dict.fromkeys(stems))


def _resolve_strongs(cur, word, book, chapter, verse):
    import re as _re
    # direct Strong's number: H7225 or G3056
    if _re.match(r'^[hg]\d+$', word):
        number = word.upper()
        cur.execute("SELECT number FROM strongs WHERE number=?", (number,))
        row = cur.fetchone()
        return row[0] if row else None

    word_stems = _stems(word.lower())

    def _gloss_conditions(stems):
        """Build SQL OR conditions using word-boundary-style LIKE patterns."""
        parts, params = [], []
        for stem in stems:
            # match stem as a whole word: at start, end, or surrounded by non-alpha chars
            likes = [f"{stem} %", f"% {stem} %", f"% {stem}", f"% {stem},%", f"% {stem};%"]
            sub_parts = []
            for like in likes:
                sub_parts.append("LOWER(s.gloss) LIKE ? OR LOWER(COALESCE(s.rich_gloss,'')) LIKE ?")
                params += [like, like]
            parts.append(f"({' OR '.join(sub_parts)})")
        return " OR ".join(parts), params

    cond, cond_params = _gloss_conditions(word_stems)

    # verse scope — find Strong's number used in that exact verse whose gloss matches
    if book and chapter and verse:
        cur.execute(
            f"""
            SELECT vw.strongs_number FROM verse_words vw
            JOIN strongs s ON s.number = vw.strongs_number
            WHERE vw.book=? AND vw.chapter=? AND vw.verse=? AND ({cond})
            LIMIT 1
            """,
            (book, chapter, verse, *cond_params),
        )
        row = cur.fetchone()
        if row:
            return row[0]

    # chapter/book scope — find Strong's numbers that appear in KJV verses
    # containing the English word AND whose gloss matches the stem.
    # Combining both filters avoids common particles (H0853 etc.) that appear
    # in every verse but have no semantic match to the search word.
    for stem in word_stems:
        like_text = f"% {stem}%"
        gloss_likes = [f"{stem} %", f"% {stem} %", f"% {stem}", f"% {stem},%", f"% {stem};%"]
        gcond = " OR ".join(["LOWER(s.gloss) LIKE ?" for _ in gloss_likes])

        if book and chapter:
            cur.execute(
                f"""
                SELECT vw.strongs_number, COUNT(*) as cnt FROM verse_words vw
                JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
                JOIN strongs s ON s.number = vw.strongs_number
                WHERE vw.book=? AND vw.chapter=? AND v.translation='KJV'
                  AND LOWER(v.text) LIKE ?
                  AND ({gcond})
                GROUP BY vw.strongs_number ORDER BY cnt DESC LIMIT 1
                """,
                (book, chapter, like_text, *gloss_likes),
            )
        elif book:
            cur.execute(
                f"""
                SELECT vw.strongs_number, COUNT(*) as cnt FROM verse_words vw
                JOIN verses v ON v.book=vw.book AND v.chapter=vw.chapter AND v.verse=vw.verse
                JOIN strongs s ON s.number = vw.strongs_number
                WHERE vw.book=? AND v.translation='KJV'
                  AND LOWER(v.text) LIKE ?
                  AND ({gcond})
                GROUP BY vw.strongs_number ORDER BY cnt DESC LIMIT 1
                """,
                (book, like_text, *gloss_likes),
            )
        else:
            break

        row = cur.fetchone()
        if row:
            return row[0]

    # full-Bible fallback: prefer language matching the book's testament
    lang = "Hebrew" if book in OT_BOOKS else "Greek" if book else None
    for stem in word_stems:
        likes = [f"{stem} %", f"% {stem} %", f"% {stem}", f"% {stem},%", f"% {stem};%"]
        conds = " OR ".join(["LOWER(gloss) LIKE ?" for _ in likes])
        if lang:
            cur.execute(
                f"SELECT number FROM strongs WHERE ({conds}) AND language=? LIMIT 1",
                (*likes, lang),
            )
        else:
            cur.execute(
                f"SELECT number FROM strongs WHERE ({conds}) LIMIT 1",
                likes,
            )
        row = cur.fetchone()
        if row:
            return row[0]

    return None


def _paginate(results, word, total):
    page = 0
    while True:
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        chunk = results[start:end]

        table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
        table.add_column("Reference", style="bold yellow", min_width=20)
        table.add_column("Verse (keyword in context)", style="white")

        for book, chapter, verse, text in chunk:
            ref = f"{book} {chapter}:{verse}"
            highlighted = _highlight(text, word)
            table.add_row(ref, highlighted)

        console.print(table)

        if end >= total:
            break

        console.print(
            f"\n  [dim]Showing {end} of {total}  ·  [n] next page  ·  [q] quit[/dim]"
        )
        key = console.input("  ").strip().lower()
        if key == "q":
            break
        page += 1


def _highlight(text, word):
    result = Text()
    lower_text = text.lower()
    lower_word = word.lower()
    idx = 0
    while True:
        pos = lower_text.find(lower_word, idx)
        if pos == -1:
            result.append(text[idx:])
            break
        result.append(text[idx:pos])
        result.append(text[pos:pos + len(word)], style="bold yellow on dark_green")
        idx = pos + len(word)
    return result


def _book_frequency(results):
    freq = {}
    for book, _, _, _ in results:
        freq[book] = freq.get(book, 0) + 1

    sorted_books = sorted(freq.items(), key=lambda x: -x[1])[:10]
    max_count = sorted_books[0][1] if sorted_books else 1

    console.print()
    console.rule("[dim]Book Frequency[/dim]", style="dim")
    console.print()

    for book, count in sorted_books:
        bar_len = int((count / max_count) * 20)
        bar = "█" * bar_len
        console.print(f"  [yellow]{book:<20}[/yellow] [green]{bar:<20}[/green]  [green]{count}[/green]")

    if len(freq) > 10:
        console.print(f"  [dim]… {len(freq) - 10} more books[/dim]")

    console.print()
    console.rule(style="dim")
    console.print()
