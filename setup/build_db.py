"""
Run this once to build bible.db from open public domain datasets.
Usage: python setup/build_db.py
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from setup import load_verses, load_strongs, load_xref, load_verse_words, load_translations, load_rich_lexicon

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "bible.db")


def create_tables(cur):
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS verses (
            book        TEXT NOT NULL,
            chapter     INTEGER NOT NULL,
            verse       INTEGER NOT NULL,
            text        TEXT NOT NULL,
            translation TEXT DEFAULT 'KJV',
            PRIMARY KEY (book, chapter, verse, translation)
        );

        CREATE TABLE IF NOT EXISTS strongs (
            number          TEXT PRIMARY KEY,
            language        TEXT,
            word            TEXT,
            transliteration TEXT,
            gloss           TEXT,
            definition      TEXT,
            root            TEXT
        );

        CREATE TABLE IF NOT EXISTS verse_words (
            book            TEXT NOT NULL,
            chapter         INTEGER NOT NULL,
            verse           INTEGER NOT NULL,
            word_position   INTEGER NOT NULL,
            english_word    TEXT,
            strongs_number  TEXT,
            PRIMARY KEY (book, chapter, verse, word_position)
        );

        CREATE TABLE IF NOT EXISTS xrefs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            from_book    TEXT NOT NULL,
            from_chapter INTEGER NOT NULL,
            from_verse   INTEGER NOT NULL,
            to_book      TEXT NOT NULL,
            to_chapter   INTEGER NOT NULL,
            to_verse     INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_verses_ref    ON verses (book, chapter, verse);
        CREATE INDEX IF NOT EXISTS idx_xref_from     ON xrefs (from_book, from_chapter, from_verse);
        CREATE INDEX IF NOT EXISTS idx_vw_strongs    ON verse_words (strongs_number);
        CREATE INDEX IF NOT EXISTS idx_vw_word       ON verse_words (english_word);
    """)


def main():
    print("\n=== Bybletools DB Builder ===\n")

    print("[1/6] Downloading source data...")
    load_verses.download()
    load_strongs.download()
    load_xref.download()
    load_verse_words.download()
    print("  Downloading additional translations...")
    load_translations.download()
    print("  Downloading rich lexicons (BDB/Thayer's)...")
    load_rich_lexicon.download()

    print("\n[2/4] Creating database schema...")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    create_tables(cur)
    con.commit()
    print("  Tables created.")

    print("\n[3/5] Loading data...")
    load_verses.load(cur)
    con.commit()
    load_strongs.load(cur)
    con.commit()
    load_xref.load(cur)
    con.commit()
    load_verse_words.load(cur)
    con.commit()

    print("\n[4/6] Loading additional translations...")
    load_translations.load(cur)
    con.commit()

    print("\n[5/6] Loading rich lexicons (BDB/Thayer's)...")
    load_rich_lexicon.load(cur)
    con.commit()

    print("\n[6/6] Finalizing...")
    cur.execute("PRAGMA optimize;")
    con.close()

    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\n  bible.db created — {size_mb:.1f} MB")
    print("\n=== Done! Run: python study.py John 3:16 ===\n")


if __name__ == "__main__":
    main()
