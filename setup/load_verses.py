import json
import urllib.request
import os

BASE_URL = "https://raw.githubusercontent.com/aruljohn/Bible-kjv/master"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

BOOKS = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
    "1Samuel","2Samuel","1Kings","2Kings","1Chronicles","2Chronicles","Ezra","Nehemiah",
    "Esther","Job","Psalms","Proverbs","Ecclesiastes","SongofSolomon","Isaiah","Jeremiah",
    "Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah",
    "Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew","Mark","Luke",
    "John","Acts","Romans","1Corinthians","2Corinthians","Galatians","Ephesians",
    "Philippians","Colossians","1Thessalonians","2Thessalonians","1Timothy","2Timothy",
    "Titus","Philemon","Hebrews","James","1Peter","2Peter","1John","2John","3John",
    "Jude","Revelation",
]

# Map filename → display name stored in DB
DISPLAY_NAME = {
    "1Samuel": "1 Samuel", "2Samuel": "2 Samuel",
    "1Kings": "1 Kings", "2Kings": "2 Kings",
    "1Chronicles": "1 Chronicles", "2Chronicles": "2 Chronicles",
    "SongofSolomon": "Song of Solomon",
    "1Corinthians": "1 Corinthians", "2Corinthians": "2 Corinthians",
    "1Thessalonians": "1 Thessalonians", "2Thessalonians": "2 Thessalonians",
    "1Timothy": "1 Timothy", "2Timothy": "2 Timothy",
    "1Peter": "1 Peter", "2Peter": "2 Peter",
    "1John": "1 John", "2John": "2 John", "3John": "3 John",
}


def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    books_dir = os.path.join(DATA_DIR, "books")
    os.makedirs(books_dir, exist_ok=True)
    print("  Downloading KJV Bible (66 books)...")
    for book in BOOKS:
        path = os.path.join(books_dir, f"{book}.json")
        if os.path.exists(path):
            continue
        url = f"{BASE_URL}/{book}.json"
        urllib.request.urlretrieve(url, path)
    print("  Done.")


def load(cur):
    books_dir = os.path.join(DATA_DIR, "books")
    rows = []
    for book_file in BOOKS:
        path = os.path.join(books_dir, f"{book_file}.json")
        if not os.path.exists(path):
            print(f"  Missing: {book_file}.json — skipping")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        book_name = DISPLAY_NAME.get(book_file, data.get("book", book_file))
        for chapter in data.get("chapters", []):
            ch_num = int(chapter["chapter"])
            for v in chapter.get("verses", []):
                rows.append((book_name, ch_num, int(v["verse"]), v["text"].strip(), "KJV"))

    cur.executemany(
        "INSERT OR IGNORE INTO verses (book, chapter, verse, text, translation) VALUES (?,?,?,?,?)",
        rows,
    )
    print(f"  Loaded {len(rows):,} verses.")
