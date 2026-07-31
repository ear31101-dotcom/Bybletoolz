"""
Populates verse_words by parsing:
  - Hebrew OT: openscriptures/morphhb (OSIS XML, one file per book)
  - Greek NT:  STEPBible TAGNT (tab-separated, two files covering full NT)
"""
import urllib.request
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MORPH_DIR = os.path.join(DATA_DIR, "morphhb")

# --- Hebrew OT: morphhb book filenames ---
HEBREW_BOOKS = [
    ("Gen", "Genesis"), ("Exod", "Exodus"), ("Lev", "Leviticus"),
    ("Num", "Numbers"), ("Deut", "Deuteronomy"), ("Josh", "Joshua"),
    ("Judg", "Judges"), ("Ruth", "Ruth"), ("1Sam", "1 Samuel"),
    ("2Sam", "2 Samuel"), ("1Kgs", "1 Kings"), ("2Kgs", "2 Kings"),
    ("1Chr", "1 Chronicles"), ("2Chr", "2 Chronicles"), ("Ezra", "Ezra"),
    ("Neh", "Nehemiah"), ("Esth", "Esther"), ("Job", "Job"),
    ("Ps", "Psalms"), ("Prov", "Proverbs"), ("Eccl", "Ecclesiastes"),
    ("Song", "Song of Solomon"), ("Isa", "Isaiah"), ("Jer", "Jeremiah"),
    ("Lam", "Lamentations"), ("Ezek", "Ezekiel"), ("Dan", "Daniel"),
    ("Hos", "Hosea"), ("Joel", "Joel"), ("Amos", "Amos"),
    ("Obad", "Obadiah"), ("Jonah", "Jonah"), ("Mic", "Micah"),
    ("Nah", "Nahum"), ("Hab", "Habakkuk"), ("Zeph", "Zephaniah"),
    ("Hag", "Haggai"), ("Zech", "Zechariah"), ("Mal", "Malachi"),
]

MORPHHB_BASE = "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc"

# --- Greek NT: STEPBible TAGNT (two files) ---
TAGNT_FILES = {
    "tagnt_mat_jhn.txt": "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Older%20Formats/TAGNT%20Mat-Jhn%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt",
    "tagnt_act_rev.txt": "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Older%20Formats/TAGNT%20Act-Rev%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt",
}

# TAGNT book code → DB book name
TAGNT_BOOK_MAP = {
    "41_Mat": "Matthew", "42_Mrk": "Mark", "43_Luk": "Luke", "44_Jhn": "John",
    "45_Act": "Acts", "46_Rom": "Romans", "47_1Co": "1 Corinthians",
    "48_2Co": "2 Corinthians", "49_Gal": "Galatians", "50_Eph": "Ephesians",
    "51_Php": "Philippians", "52_Col": "Colossians", "53_1Th": "1 Thessalonians",
    "54_2Th": "2 Thessalonians", "55_1Ti": "1 Timothy", "56_2Ti": "2 Timothy",
    "57_Tit": "Titus", "58_Phm": "Philemon", "59_Heb": "Hebrews",
    "60_Jas": "James", "61_1Pe": "1 Peter", "62_2Pe": "2 Peter",
    "63_1Jn": "1 John", "64_2Jn": "2 John", "65_3Jn": "3 John",
    "66_Jud": "Jude", "67_Rev": "Revelation",
}


def download():
    os.makedirs(MORPH_DIR, exist_ok=True)
    print("  Downloading Hebrew morphology (39 books)...")
    for code, _ in HEBREW_BOOKS:
        path = os.path.join(MORPH_DIR, f"{code}.xml")
        if os.path.exists(path):
            continue
        url = f"{MORPHHB_BASE}/{code}.xml"
        urllib.request.urlretrieve(url, path)
    print("  Done.")

    print("  Downloading Greek NT TAGNT (2 files)...")
    for filename, url in TAGNT_FILES.items():
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            print(f"    {filename} already exists, skipping.")
            continue
        print(f"    Downloading {filename}...")
        urllib.request.urlretrieve(url, path)
    print("  Done.")


def load(cur):
    total = 0
    total += _load_hebrew(cur)
    total += _load_greek(cur)
    print(f"  Total: {total:,} word-to-Strong's mappings loaded.")


# ── Hebrew ────────────────────────────────────────────────────────────────────

# Matches <w lemma="b/7225 c/430" ...>Hebrew text</w>
_W_TAG = re.compile(r'<w[^>]+lemma="([^"]+)"[^>]*>([^<]*)</w>', re.DOTALL)
_VERSE_TAG = re.compile(r'<verse osisID="(\w+)\.(\d+)\.(\d+)"')


def _parse_lemma(raw):
    """Extract first numeric Strong's number from morphhb lemma attribute."""
    # lemma can be "b/7225" or "1254 a" or "c/d/776" — take first number
    for part in raw.replace("/", " ").split():
        part = part.strip("abcdefABCDEF")
        if part.isdigit():
            return f"H{int(part):04d}"
    return None


def _load_hebrew(cur):
    rows = []
    for code, book_name in HEBREW_BOOKS:
        path = os.path.join(MORPH_DIR, f"{code}.xml")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        current_ch = current_v = 0
        pos = 0

        for m in re.finditer(
            r'<verse osisID="[^.]+\.(\d+)\.(\d+)"|<w[^>]+lemma="([^"]+)"[^>]*>',
            content,
        ):
            if m.group(1):  # verse tag
                current_ch = int(m.group(1))
                current_v = int(m.group(2))
                pos = 0
            elif m.group(3) and current_ch:  # word tag
                strongs = _parse_lemma(m.group(3))
                if strongs:
                    rows.append((book_name, current_ch, current_v, pos, strongs))
                    pos += 1

    cur.executemany(
        "INSERT OR IGNORE INTO verse_words (book, chapter, verse, word_position, strongs_number) VALUES (?,?,?,?,?)",
        rows,
    )
    print(f"  Hebrew: loaded {len(rows):,} word mappings.")
    return len(rows)


# ── Greek ─────────────────────────────────────────────────────────────────────

def _load_greek(cur):
    rows = []

    for filename in TAGNT_FILES:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            continue

        verse_pos = {}  # (book, ch, v) → current position counter

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith(("\t", " ", "#", "=")):
                    continue
                parts = line.split("\t")
                if len(parts) < 5:
                    continue

                ref = parts[0].strip()   # e.g. "41_Mat.001.001"
                strongs_raw = parts[4].strip()  # e.g. "G0976"

                if not strongs_raw.startswith("G"):
                    continue

                # parse ref
                dot_parts = ref.split(".")
                if len(dot_parts) != 3:
                    continue
                book_code = dot_parts[0]
                book_name = TAGNT_BOOK_MAP.get(book_code)
                if not book_name:
                    continue
                try:
                    ch = int(dot_parts[1])
                    v = int(dot_parts[2])
                except ValueError:
                    continue

                key = (book_name, ch, v)
                pos = verse_pos.get(key, 0)
                verse_pos[key] = pos + 1

                # normalize Strong's: G0976 → G976, handle compounds like G2532+G1473
                first = strongs_raw.split("+")[0].split("=")[0]
                try:
                    strongs = "G" + str(int(first[1:]))
                except ValueError:
                    continue

                rows.append((book_name, ch, v, pos, strongs))

    cur.executemany(
        "INSERT OR IGNORE INTO verse_words (book, chapter, verse, word_position, strongs_number) VALUES (?,?,?,?,?)",
        rows,
    )
    print(f"  Greek: loaded {len(rows):,} word mappings.")
    return len(rows)
