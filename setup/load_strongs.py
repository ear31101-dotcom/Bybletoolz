import json
import re
import sqlite3
import urllib.request
import os

HEBREW_URL = "https://raw.githubusercontent.com/openscriptures/strongs/master/hebrew/strongs-hebrew-dictionary.js"
GREEK_URL  = "https://raw.githubusercontent.com/openscriptures/strongs/master/greek/strongs-greek-dictionary.js"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HEBREW_PATH = os.path.join(DATA_DIR, "strongs_hebrew.js")
GREEK_PATH  = os.path.join(DATA_DIR, "strongs_greek.js")


def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    for path, url, label in [(HEBREW_PATH, HEBREW_URL, "Hebrew"), (GREEK_PATH, GREEK_URL, "Greek")]:
        if os.path.exists(path):
            print(f"  strongs_{label.lower()}.json already exists, skipping.")
            continue
        print(f"  Downloading Strong's {label} lexicon...")
        urllib.request.urlretrieve(url, path)
        print(f"  Done.")


def load(cur):
    total = 0
    for path, language in [(HEBREW_PATH, "Hebrew"), (GREEK_PATH, "Greek")]:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        # strip JS wrapper: "var strongsXxxDictionary = {...}; module.exports = ..."
        match = re.search(r'=\s*(\{.*\})\s*;?\s*(?:module\.exports)?', raw, re.DOTALL)
        if not match:
            print(f"  Could not parse {path}")
            continue
        data = json.loads(match.group(1))

        rows = []
        for number, entry in data.items():
            word       = entry.get("lemma", "")
            translit   = entry.get("xlit", "") or entry.get("translit", "")
            gloss      = entry.get("strongs_def", "") or entry.get("kjv_def", "")
            definition = entry.get("strongs_def", "")
            root       = ""
            if "derivation" in entry:
                root = entry["derivation"][:120]

            rows.append((number, language, word, translit, gloss[:300], definition[:1000], root))

        cur.executemany(
            "INSERT OR IGNORE INTO strongs (number, language, word, transliteration, gloss, definition, root) VALUES (?,?,?,?,?,?,?)",
            rows,
        )
        total += len(rows)
        print(f"  Loaded {len(rows):,} {language} entries.")

    print(f"  Total: {total:,} lexicon entries.")
