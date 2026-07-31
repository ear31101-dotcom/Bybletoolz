"""
Loads four additional public-domain translations from scrollmapper/bible_databases:
  ASV  — American Standard Version (1901)
  BSB  — Berean Standard Bible (modern, CC BY)
  YLT  — Young's Literal Translation (1898)
  BBE  — Bible in Basic English (1949/1964)
"""
import json
import urllib.request
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "translations")

TRANSLATIONS = {
    "ASV": "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/ASV.json",
    "BSB": "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/BSB.json",
    "YLT": "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/YLT.json",
    "BBE": "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/BBE.json",
}


def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    for abbrev, url in TRANSLATIONS.items():
        path = os.path.join(DATA_DIR, f"{abbrev}.json")
        if os.path.exists(path):
            print(f"    {abbrev}.json already exists, skipping.")
            continue
        print(f"    Downloading {abbrev}...")
        urllib.request.urlretrieve(url, path)
    print("  Done.")


def load(cur):
    total = 0
    for abbrev in TRANSLATIONS:
        path = os.path.join(DATA_DIR, f"{abbrev}.json")
        if not os.path.exists(path):
            print(f"  {abbrev}: file not found, skipping.")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        rows = []
        for book in data.get("books", []):
            book_name = book["name"]
            for chapter in book.get("chapters", []):
                ch_num = int(chapter["chapter"])
                for v in chapter.get("verses", []):
                    rows.append((book_name, ch_num, int(v["verse"]), v["text"].strip(), abbrev))

        cur.executemany(
            "INSERT OR IGNORE INTO verses (book, chapter, verse, text, translation) VALUES (?,?,?,?,?)",
            rows,
        )
        print(f"  {abbrev}: loaded {len(rows):,} verses.")
        total += len(rows)

    print(f"  Translations total: {total:,} verses.")
