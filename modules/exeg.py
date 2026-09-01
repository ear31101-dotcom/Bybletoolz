import sqlite3
from rich.console import Console
from rich.rule import Rule

console = Console()


def _migrate(cur, con):
    """Ensure commentary table has all expected columns."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commentary'")
    if not cur.fetchone():
        return
    cur.execute("PRAGMA table_info(commentary)")
    cols = {row[1] for row in cur.fetchall()}
    changed = False
    if "verse_end" not in cols:
        cur.execute("ALTER TABLE commentary ADD COLUMN verse_end INTEGER NOT NULL DEFAULT 0")
        cur.execute("UPDATE commentary SET verse_end = verse WHERE verse_end = 0")
        changed = True
    if "chapter_end" not in cols:
        cur.execute("ALTER TABLE commentary ADD COLUMN chapter_end INTEGER NOT NULL DEFAULT 0")
        cur.execute("UPDATE commentary SET chapter_end = chapter WHERE chapter_end = 0")
        changed = True
    if "article_title" not in cols:
        cur.execute("ALTER TABLE commentary ADD COLUMN article_title TEXT")
        changed = True
    if changed:
        con.commit()


def _display_articles(cur, con, source_filter):
    """List all articles across sources, then let the user pick one to read."""
    src_clause = "AND LOWER(source_name) LIKE ?" if source_filter else ""
    src_params = [f"%{source_filter.lower()}%"] if source_filter else []

    cur.execute(
        f"""
        SELECT source_name, article_title
        FROM commentary
        WHERE book='Article'
        {src_clause}
        ORDER BY source_name, article_title
        """,
        src_params,
    )
    rows = cur.fetchall()

    if not rows:
        console.print()
        if source_filter:
            console.print(f"  [yellow]No articles found matching \"{source_filter}\".[/yellow]")
        else:
            console.print("  [yellow]No articles found in any imported source.[/yellow]")
            console.print("  [dim]Add article rows (book='Article', assignment_source='article') to a CSV and re-import.[/dim]")
        console.print()
        return

    console.print()
    console.rule("[bold cyan]Articles[/bold cyan]", style="dim")
    console.print()

    # deduplicate and number
    seen = []
    for source_name, title in rows:
        key = (source_name, title)
        if key not in seen:
            seen.append(key)

    for i, (source_name, title) in enumerate(seen, 1):
        console.print(f"  [bold yellow]{i:>2}.[/bold yellow]  {title}  [dim]({source_name})[/dim]")

    console.print()

    try:
        raw = input("  Enter number to read (or press Enter to exit): ").strip()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return

    if not raw:
        console.print()
        return

    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(seen)):
            raise ValueError
    except ValueError:
        console.print("  [red]Invalid selection.[/red]")
        console.print()
        return

    chosen_source, chosen_title = seen[idx]

    cur.execute(
        "SELECT text FROM commentary WHERE book='Article' AND source_name=? AND article_title=? ORDER BY id",
        (chosen_source, chosen_title),
    )
    article_rows = cur.fetchall()
    full_text = "\n\n".join(r[0] for r in article_rows)

    console.print()
    console.rule(f"[bold cyan]{chosen_title}[/bold cyan]", style="dim")
    console.print(f"  [dim]{chosen_source}[/dim]")
    console.print()
    console.print(f"  {full_text}", soft_wrap=True)
    console.print()
    console.rule(style="dim")
    console.print()


def display(parsed, db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    book = parsed["book"]
    chapter = parsed["chapter"]
    v_start = parsed["verse_start"]
    v_end = parsed["verse_end"] or v_start
    source_filter = parsed["word"]  # optional source name filter

    _migrate(cur, con)

    # ── byble exeg (no book) → article index ─────────────────────────────────
    if book is None:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commentary'")
        if not cur.fetchone():
            console.print()
            console.print("  [yellow]No commentary data imported yet.[/yellow]")
            console.print("  [dim]Import a source with:  byble import exeg <file> \"Source Name\"[/dim]")
            console.print()
            con.close()
            return
        _display_articles(cur, con, source_filter)
        con.close()
        return

    book_scope    = chapter is None   # True when no chapter given — show book intro
    chapter_scope = not book_scope and v_start is None  # whole chapter

    if book_scope:
        ref = book
    elif chapter_scope:
        ref = f"{book} {chapter}"
    elif v_start == v_end:
        ref = f"{book} {chapter}:{v_start}"
    else:
        ref = f"{book} {chapter}:{v_start}-{v_end}"

    # check table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commentary'")
    if not cur.fetchone():
        console.print()
        console.print("  [yellow]No commentary data imported yet.[/yellow]")
        console.print("  [dim]Import a source with:  byble import exeg <file.cmtx> \"Source Name\"[/dim]")
        console.print()
        con.close()
        return

    console.print()
    console.rule(f"[bold cyan]{ref}  —  Exegesis[/bold cyan]", style="dim")
    console.print()

    if not book_scope:
        if chapter_scope:
            cur.execute(
                "SELECT verse, text FROM verses WHERE book=? AND chapter=? AND translation='KJV' ORDER BY verse",
                (book, chapter),
            )
        else:
            cur.execute(
                "SELECT verse, text FROM verses WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? AND translation='KJV' ORDER BY verse",
                (book, chapter, v_start, v_end),
            )
        for verse_num, verse_text in cur.fetchall():
            console.print(f"  [bold yellow]{verse_num}[/bold yellow] [dim]{verse_text}[/dim]")
        console.print()
        console.rule(style="dim")
        console.print()

    # Overlap condition for a note to match target range (book, ch, [v_start, v_end]):
    #   note_start <= target_end  AND  note_end >= target_start
    # where start/end are (chapter, verse) pairs compared lexicographically via
    # (chapter * 1000 + verse) to handle cross-chapter notes cleanly.
    #
    # For chapter scope (no verse): note overlaps if chapter <= ch <= chapter_end.

    src_clause = "AND LOWER(source_name) LIKE ?" if source_filter else ""
    src_params = [f"%{source_filter.lower()}%"] if source_filter else []

    if book_scope:
        # book introductions stored at chapter=0, verse=0
        cur.execute(
            f"""
            SELECT source_name, chapter, verse, chapter_end, verse_end, text FROM commentary
            WHERE book=? AND chapter=0 AND verse=0
            {src_clause}
            ORDER BY source_name
            """,
            (book, *src_params),
        )
    elif chapter_scope:
        cur.execute(
            f"""
            SELECT source_name, chapter, verse, chapter_end, verse_end, text FROM commentary
            WHERE book=? AND chapter <= ? AND chapter_end >= ?
            {src_clause}
            ORDER BY chapter, verse, source_name
            """,
            (book, chapter, chapter, *src_params),
        )
    else:
        # note overlaps [v_start..v_end] within chapter, accounting for cross-chapter notes
        target_start = chapter * 1000 + v_start
        target_end   = chapter * 1000 + v_end
        cur.execute(
            f"""
            SELECT source_name, chapter, verse, chapter_end, verse_end, text FROM commentary
            WHERE book=?
              AND (chapter * 1000 + verse) <= ?
              AND (chapter_end * 1000 + verse_end) >= ?
            {src_clause}
            ORDER BY source_name, chapter, verse
            """,
            (book, target_end, target_start, *src_params),
        )

    rows = cur.fetchall()

    # get all known commentary sources for coverage feedback
    cur2 = con.cursor()
    cur2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commentary_sources'")
    all_sources = []
    if cur2.fetchone():
        if source_filter:
            cur2.execute(
                "SELECT source_name, books_covered FROM commentary_sources WHERE LOWER(source_name) LIKE ?",
                (f"%{source_filter.lower()}%",),
            )
        else:
            cur2.execute("SELECT source_name, books_covered FROM commentary_sources ORDER BY source_name")
        all_sources = cur2.fetchall()

    con.close()

    if not rows:
        if source_filter:
            if not all_sources:
                console.print(f"  [yellow]No source matching \"{source_filter}\" found.[/yellow]")
                console.print("  [dim]Run: byble import list  to see available sources.[/dim]")
            else:
                for sname, coverage in all_sources:
                    console.print(f"  [yellow]{sname}[/yellow] [dim]({coverage})[/dim] — no note for {ref}")
        else:
            if not all_sources:
                console.print("  [yellow]No commentary sources imported yet.[/yellow]")
                console.print("  [dim]Import a source with:  byble import exeg <file> \"Source Name\"[/dim]")
            else:
                for sname, coverage in all_sources:
                    console.print(f"  [dim]{sname} ({coverage}) — no note for {ref}[/dim]")
        console.print()
        return

    def _range_label(ch_s, vs, ch_e, ve):
        """Human-readable label for a note's anchor range."""
        if ch_s == ch_e:
            if vs == ve:
                return f"Verse {vs}"
            return f"Verses {vs}–{ve}"
        return f"{ch_s}:{vs}–{ch_e}:{ve}"

    if book_scope:
        if not rows:
            console.print(f"  [dim]No book introduction found for {book}.[/dim]")
            console.print()
        else:
            for source_name, *_, text in rows:
                console.rule(f"[bold green]{source_name}[/bold green]", style="dim green")
                console.print()
                console.print(f"  {text}", soft_wrap=True)
                console.print()
        return

    elif chapter_scope:
        # group by anchor verse (start), then source within each verse
        by_verse = {}
        for source_name, ch_s, vs, ch_e, ve, text in rows:
            by_verse.setdefault((ch_s, vs), []).append((source_name, ch_e, ve, text))

        for (ch_s, vs) in sorted(by_verse):
            entries = by_verse[(ch_s, vs)]
            console.rule(f"[bold yellow]Verse {vs}[/bold yellow]", style="dim yellow")
            console.print()
            for source_name, ch_e, ve, text in entries:
                is_range = (ch_s, vs) != (ch_e, ve)
                if is_range:
                    console.print(f"  [bold green]{source_name}[/bold green]  [dim]({_range_label(ch_s, vs, ch_e, ve)})[/dim]")
                else:
                    console.print(f"  [bold green]{source_name}[/bold green]")
                console.print()
                console.print(f"  {text}", soft_wrap=True)
                console.print()
    else:
        # group by source_name (verse/range scope)
        sources = {}
        for source_name, ch_s, vs, ch_e, ve, text in rows:
            sources.setdefault(source_name, []).append((ch_s, vs, ch_e, ve, text))

        silent_sources = [(sn, cov) for sn, cov in all_sources if sn not in sources]

        for source_name, entries in sources.items():
            console.rule(f"[bold green]{source_name}[/bold green]", style="dim green")
            console.print()
            for ch_s, vs, ch_e, ve, text in entries:
                is_range = (ch_s, vs) != (ch_e, ve)
                show_label = (v_start != v_end) or is_range
                if show_label:
                    console.print(f"  [dim]{_range_label(ch_s, vs, ch_e, ve)}:[/dim]")
                console.print(f"  {text}", soft_wrap=True)
                console.print()

        if silent_sources and not source_filter:
            for sname, coverage in silent_sources:
                console.print(f"  [dim]{sname} ({coverage}) — no note for {ref}[/dim]")
            console.print()

    console.rule(style="dim")
    console.print()
