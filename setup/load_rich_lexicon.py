"""
Loads richer lexicon definitions from STEPBible:
  TBESH — Hebrew (based on BDB / Brown-Driver-Briggs)
  TBESG — Greek  (based on Abbott-Smith / Thayer's tradition)

These replace the thin Strong's gloss with full scholarly definitions.
Fields are added to the existing strongs table as:
  rich_definition  — full expanded definition
  rich_gloss       — concise gloss from STEPBible
"""
import urllib.request
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

HEBREW_URL = "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Lexicons/TBESH%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Hebrew%20-%20STEPBible.org%20CC%20BY.txt"
GREEK_URL  = "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Lexicons/TBESG%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Greek%20-%20STEPBible.org%20CC%20BY.txt"

HEBREW_PATH = os.path.join(DATA_DIR, "tbesh.txt")
GREEK_PATH  = os.path.join(DATA_DIR, "tbesg.txt")


def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    for path, url, label in [(HEBREW_PATH, HEBREW_URL, "Hebrew TBESH"), (GREEK_PATH, GREEK_URL, "Greek TBESG")]:
        if os.path.exists(path):
            print(f"    {label} already exists, skipping.")
            continue
        print(f"    Downloading {label}...")
        urllib.request.urlretrieve(url, path)
    print("  Done.")


def _add_columns_if_needed(cur):
    existing = {row[1] for row in cur.execute("PRAGMA table_info(strongs)").fetchall()}
    if "rich_definition" not in existing:
        cur.execute("ALTER TABLE strongs ADD COLUMN rich_definition TEXT")
    if "rich_gloss" not in existing:
        cur.execute("ALTER TABLE strongs ADD COLUMN rich_gloss TEXT")


def _clean_html(text):
    """Strip HTML tags and clean up whitespace."""
    text = re.sub(r'<BR\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<b>(.*?)</b>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<i>(.*?)</i>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<ref=[\'"][^"\']*[\'"]>(.*?)</ref>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'__+', '  ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def load(cur):
    _add_columns_if_needed(cur)

    total_h = _load_file(cur, HEBREW_PATH, "H")
    total_g = _load_file(cur, GREEK_PATH,  "G")
    print(f"  Rich lexicon: updated {total_h:,} Hebrew + {total_g:,} Greek entries.")


def _load_file(cur, path, prefix):
    if not os.path.exists(path):
        print(f"  {path} not found, skipping.")
        return 0

    updates = {}

    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith(("=", "\t", " ", "#", "$", "-")):
                continue

            parts = line.split("\t")
            if len(parts) < 7:
                continue

            raw_number = parts[0].strip()   # e.g. H0001 or G0001
            raw_gloss  = parts[6].strip()   # concise gloss
            raw_def    = parts[7].strip() if len(parts) > 7 else ""

            # Normalize number: H0001 → H1, G0003 → G3
            if not raw_number.startswith(prefix):
                continue
            try:
                num_int = int(raw_number[1:])
            except ValueError:
                continue
            number = f"{prefix}{num_int}"

            # Only keep the base entry (skip disambiguated variants like H0001G, H0001H)
            raw_id = parts[1].strip() if len(parts) > 1 else ""
            if "=" in raw_id:
                variant = raw_id.split("=")[0].strip()
                # skip if variant has a letter suffix beyond the number
                suffix = variant[len(raw_number):]
                if suffix and suffix not in ("", " "):
                    continue

            clean_def  = _clean_html(raw_def)
            clean_gloss = _clean_html(raw_gloss)

            if number not in updates:
                updates[number] = (clean_gloss, clean_def)

    rows = [(gloss, defn, num) for num, (gloss, defn) in updates.items()]
    cur.executemany(
        "UPDATE strongs SET rich_gloss=?, rich_definition=? WHERE number=?",
        rows,
    )
    return len(rows)
