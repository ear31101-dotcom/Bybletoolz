import sqlite3
from rich.console import Console
from rich.text import Text

console = Console()

VALID_TRANSLATIONS = {"KJV", "ASV", "BSB", "YLT", "BBE"}
DEFAULT_TRANSLATION = "KJV"


def display(parsed, db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    book    = parsed["book"]
    chapter = parsed["chapter"]
    v_start = parsed["verse_start"]
    v_end   = parsed["verse_end"] or v_start
    translation = (parsed.get("translation") or DEFAULT_TRANSLATION).upper()
    chapter_scope = v_start is None

    if translation not in VALID_TRANSLATIONS:
        console.print(
            f"[yellow]Unknown translation '{translation}'. "
            f"Available: {', '.join(sorted(VALID_TRANSLATIONS))}.[/yellow]"
        )
        translation = DEFAULT_TRANSLATION

    if chapter_scope:
        cur.execute(
            "SELECT verse, text FROM verses "
            "WHERE book=? AND chapter=? AND translation=? "
            "ORDER BY verse",
            (book, chapter, translation),
        )
        ref = f"{book} {chapter}"
    else:
        cur.execute(
            "SELECT verse, text FROM verses "
            "WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? AND translation=? "
            "ORDER BY verse",
            (book, chapter, v_start, v_end, translation),
        )
        ref = (
            f"{book} {chapter}:{v_start}"
            if v_start == v_end
            else f"{book} {chapter}:{v_start}-{v_end}"
        )

    rows = cur.fetchall()
    con.close()

    if not rows:
        console.print(f"[red]No verses found for {ref} ({translation})[/red]")
        return

    console.print()
    console.rule(f"[bold cyan]{ref}[/bold cyan]  [dim]{translation}[/dim]", style="dim")
    console.print()

    for verse_num, text in rows:
        line = Text()
        line.append(f"{verse_num} ", style="bold yellow")
        line.append(text, style="white")
        console.print(line, soft_wrap=True)

    console.print()
    console.rule(style="dim")
    console.print()
