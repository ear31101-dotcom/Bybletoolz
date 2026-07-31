import sqlite3
from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()


def display(parsed, db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    book = parsed["book"]
    chapter = parsed["chapter"]
    v_start = parsed["verse_start"]
    v_end = parsed["verse_end"] or v_start
    style = parsed["cross_style"]  # "flat" or "grp"

    ref = f"{book} {chapter}:{v_start}" if v_start == v_end else f"{book} {chapter}:{v_start}-{v_end}"

    # fetch source verses
    cur.execute(
        "SELECT verse, text FROM verses WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? ORDER BY verse",
        (book, chapter, v_start, v_end),
    )
    source_verses = cur.fetchall()
    if not source_verses:
        console.print(f"[red]Verse not found: {ref}[/red]")
        con.close()
        return

    console.print()
    console.rule(f"[bold cyan]{ref}  —  Cross-Reference[/bold cyan]", style="dim")
    console.print()

    # check whether custom_xrefs table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='custom_xrefs'")
    has_custom = cur.fetchone() is not None

    # fetch cross-references for each verse in range (built-in + custom merged)
    xref_data = {}
    for verse_num, verse_text in source_verses:
        cur.execute(
            """
            SELECT x.to_book, x.to_chapter, x.to_verse, v.text
            FROM xrefs x
            LEFT JOIN verses v ON v.book=x.to_book AND v.chapter=x.to_chapter AND v.verse=x.to_verse
            WHERE x.from_book=? AND x.from_chapter=? AND x.from_verse=?
            ORDER BY x.to_book, x.to_chapter, x.to_verse
            """,
            (book, chapter, verse_num),
        )
        refs = cur.fetchall()

        if has_custom:
            cur.execute(
                """
                SELECT cx.to_book, cx.to_chapter, cx.to_verse, v.text
                FROM custom_xrefs cx
                LEFT JOIN verses v ON v.book=cx.to_book AND v.chapter=cx.to_chapter AND v.verse=cx.to_verse
                WHERE cx.from_book=? AND cx.from_chapter=? AND cx.from_verse=?
                ORDER BY cx.to_book, cx.to_chapter, cx.to_verse
                """,
                (book, chapter, verse_num),
            )
            custom = cur.fetchall()
            # merge, deduplicate by (book, chapter, verse)
            seen = {(r[0], r[1], r[2]) for r in refs}
            refs = refs + [r for r in custom if (r[0], r[1], r[2]) not in seen]

        xref_data[verse_num] = (verse_text, refs)

    con.close()

    total = sum(len(refs) for _, refs in xref_data.values())

    if style == "grp":
        _render_grouped(xref_data, v_start, v_end)
    else:
        _render_flat(source_verses, xref_data)

    console.print(f"  [green]{total} cross-references[/green]  [dim]across {v_end - v_start + 1} verse(s)[/dim]")
    console.print()
    console.rule(style="dim")
    console.print()


def _render_grouped(xref_data, v_start, v_end):
    for verse_num, (verse_text, refs) in xref_data.items():
        console.print(f"  [bold red]{_book_from_context(xref_data, verse_num)} {verse_num}[/bold red]  [dim]\"{verse_text[:60]}{'…' if len(verse_text) > 60 else ''}\"[/dim]")
        if not refs:
            console.print("   [dim]No cross-references found.[/dim]")
        for i, (to_book, to_ch, to_v, to_text) in enumerate(refs):
            is_last = i == len(refs) - 1
            prefix = "  └─" if is_last else "  ├─"
            to_ref = f"{to_book} {to_ch}:{to_v}"
            console.print(f"  [dim]{prefix}[/dim] [yellow]{to_ref:<22}[/yellow] [white]{to_text or '[text unavailable]'}[/white]", soft_wrap=True)
        console.print()


def _render_flat(source_verses, xref_data):
    # print full passage text first
    for verse_num, verse_text in source_verses:
        console.print(f"  [bold yellow]{verse_num}[/bold yellow] [dim]{verse_text}[/dim]")
    console.print()
    console.rule(style="dim")
    console.print()

    # collect all refs with tags
    all_refs = []
    for verse_num, (verse_text, refs) in xref_data.items():
        for to_book, to_ch, to_v, to_text in refs:
            all_refs.append((to_book, to_ch, to_v, to_text))

    if not all_refs:
        console.print("  [dim]No cross-references found.[/dim]")
        return

    for to_book, to_ch, to_v, to_text in all_refs:
        to_ref = f"{to_book} {to_ch}:{to_v}"
        console.print(f"  [yellow]{to_ref}[/yellow]")
        if to_text:
            console.print(f"  [white]{to_text}[/white]", soft_wrap=True)
        else:
            console.print("  [dim][text unavailable][/dim]")
        console.print()


def _book_from_context(xref_data, verse_num):
    # helper — returns book name (we don't store it per-verse so grab from parent parsed)
    return ""
