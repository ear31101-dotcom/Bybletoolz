import sqlite3
import urllib.request
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# scrollmapper cross-reference SQL dumps (public domain, community-voted)
XREF_BASE = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/psql/extras"
NUM_FILES = 7  # cross_references_0.sql through cross_references_6.sql


def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    for i in range(NUM_FILES):
        path = os.path.join(DATA_DIR, f"xrefs_{i}.sql")
        if os.path.exists(path):
            print(f"  xrefs_{i}.sql already exists, skipping.")
            continue
        url = f"{XREF_BASE}/cross_references_{i}.sql"
        print(f"  Downloading cross_references_{i}.sql...")
        urllib.request.urlretrieve(url, path)
    print("  Done.")


def load(cur):
    rows = []
    pattern = re.compile(
        r"VALUES\s*\(\s*'([^']+)'\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'([^']+)'\s*,\s*(\d+)\s*,\s*(\d+)",
        re.IGNORECASE,
    )

    for i in range(NUM_FILES):
        path = os.path.join(DATA_DIR, f"xrefs_{i}.sql")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    rows.append((
                        m.group(1), int(m.group(2)), int(m.group(3)),
                        m.group(4), int(m.group(5)), int(m.group(6)),
                    ))

    cur.executemany(
        "INSERT OR IGNORE INTO xrefs (from_book, from_chapter, from_verse, to_book, to_chapter, to_verse) VALUES (?,?,?,?,?,?)",
        rows,
    )
    print(f"  Loaded {len(rows):,} cross-references.")
