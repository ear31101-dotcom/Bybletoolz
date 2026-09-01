import re

BOOK_ALIASES = {
    "gn": "Genesis", "gen": "Genesis", "genesis": "Genesis",
    "ex": "Exodus", "exo": "Exodus", "exodus": "Exodus",
    "lv": "Leviticus", "lev": "Leviticus", "leviticus": "Leviticus",
    "nu": "Numbers", "num": "Numbers", "numbers": "Numbers",
    "dt": "Deuteronomy", "deu": "Deuteronomy", "deut": "Deuteronomy", "deuteronomy": "Deuteronomy",
    "jos": "Joshua", "joshua": "Joshua",
    "jdg": "Judges", "judges": "Judges",
    "rut": "Ruth", "ruth": "Ruth",
    "1sa": "1 Samuel", "1sam": "1 Samuel", "1samuel": "1 Samuel",
    "2sa": "2 Samuel", "2sam": "2 Samuel", "2samuel": "2 Samuel",
    "1ki": "1 Kings", "1kgs": "1 Kings", "1kings": "1 Kings",
    "2ki": "2 Kings", "2kgs": "2 Kings", "2kings": "2 Kings",
    "1ch": "1 Chronicles", "1chr": "1 Chronicles", "1chronicles": "1 Chronicles",
    "2ch": "2 Chronicles", "2chr": "2 Chronicles", "2chronicles": "2 Chronicles",
    "ezr": "Ezra", "ezra": "Ezra",
    "neh": "Nehemiah", "nehemiah": "Nehemiah",
    "est": "Esther", "esther": "Esther",
    "job": "Job",
    "psa": "Psalms", "ps": "Psalms", "psalm": "Psalms", "psalms": "Psalms",
    "pro": "Proverbs", "prov": "Proverbs", "proverbs": "Proverbs",
    "ecc": "Ecclesiastes", "eccl": "Ecclesiastes", "ecclesiastes": "Ecclesiastes",
    "sng": "Song of Solomon", "song": "Song of Solomon",
    "is": "Isaiah", "isa": "Isaiah", "isaiah": "Isaiah",
    "jer": "Jeremiah", "jeremiah": "Jeremiah",
    "lam": "Lamentations", "lamentations": "Lamentations",
    "ezk": "Ezekiel", "eze": "Ezekiel", "ezekiel": "Ezekiel",
    "dan": "Daniel", "daniel": "Daniel",
    "hos": "Hosea", "hosea": "Hosea",
    "joe": "Joel", "joel": "Joel",
    "amo": "Amos", "amos": "Amos",
    "oba": "Obadiah", "obadiah": "Obadiah",
    "jon": "Jonah", "jonah": "Jonah",
    "mic": "Micah", "micah": "Micah",
    "nam": "Nahum", "nahum": "Nahum",
    "hab": "Habakkuk", "habakkuk": "Habakkuk",
    "zep": "Zephaniah", "zephaniah": "Zephaniah",
    "hag": "Haggai", "haggai": "Haggai",
    "zec": "Zechariah", "zech": "Zechariah", "zechariah": "Zechariah",
    "mal": "Malachi", "malachi": "Malachi",
    "mt": "Matthew", "mat": "Matthew", "matt": "Matthew", "matthew": "Matthew",
    "mk": "Mark", "mar": "Mark", "mark": "Mark",
    "lk": "Luke", "luk": "Luke", "luke": "Luke",
    "joh": "John", "jn": "John", "john": "John",
    "ac": "Acts", "act": "Acts", "acts": "Acts",
    "rom": "Romans", "romans": "Romans",
    "1co": "1 Corinthians", "1cor": "1 Corinthians", "1corinthians": "1 Corinthians",
    "2co": "2 Corinthians", "2cor": "2 Corinthians", "2corinthians": "2 Corinthians",
    "gal": "Galatians", "galatians": "Galatians",
    "eph": "Ephesians", "ephesians": "Ephesians",
    "php": "Philippians", "phil": "Philippians", "philippians": "Philippians",
    "col": "Colossians", "colossians": "Colossians",
    "1th": "1 Thessalonians", "1thes": "1 Thessalonians", "1thessalonians": "1 Thessalonians",
    "2th": "2 Thessalonians", "2thes": "2 Thessalonians", "2thessalonians": "2 Thessalonians",
    "1ti": "1 Timothy", "1tim": "1 Timothy", "1timothy": "1 Timothy",
    "2ti": "2 Timothy", "2tim": "2 Timothy", "2timothy": "2 Timothy",
    "tit": "Titus", "titus": "Titus",
    "phm": "Philemon", "philemon": "Philemon",
    "heb": "Hebrews", "hebrews": "Hebrews",
    "jas": "James", "james": "James",
    "1pe": "1 Peter", "1pet": "1 Peter", "1peter": "1 Peter",
    "2pe": "2 Peter", "2pet": "2 Peter", "2peter": "2 Peter",
    "1jo": "1 John", "1jn": "1 John", "1john": "1 John",
    "2jo": "2 John", "2jn": "2 John", "2john": "2 John",
    "3jo": "3 John", "3jn": "3 John", "3john": "3 John",
    "jud": "Jude", "jude": "Jude",
    "rv": "Revelation", "rev": "Revelation", "revelation": "Revelation",
}

MODES = {"lex", "con", "cross", "exeg"}
CROSS_STYLES = {"flat", "grp"}
TRANSLATIONS = {"kjv", "asv", "bsb", "ylt", "bbe"}


def parse_input(args):
    """
    Parse sys.argv[1:] into a structured dict.

    Supported reference scopes:
      byble Con H7225              — full-Bible scope (mode first, no ref)
      byble Gen Con H7225          — book scope
      byble Gen 1 Con H7225        — chapter scope
      byble Gen 1:1 Con H7225      — verse scope (original behaviour)
      byble Gen 1:1-5 Con H7225    — verse-range scope

    Returns:
      {
        book, chapter, verse_start, verse_end,
        mode, word, cross_style, translation, error
      }
    """
    tokens = list(args)
    result = {
        "book": None, "chapter": None,
        "verse_start": None, "verse_end": None,
        "mode": None, "word": None,
        "cross_style": "flat", "translation": "KJV", "error": None,
    }

    if not tokens:
        result["error"] = "No input provided. Example: byble John 3:16"
        return result

    # --- check for mode-first syntax: byble Con H7225  OR  byble Exeg ---
    if tokens[0].lower() in MODES:
        for token in tokens:
            lower = token.lower()
            if lower in MODES:
                result["mode"] = lower
            elif lower in TRANSLATIONS:
                result["translation"] = lower.upper()
            else:
                result["word"] = token
        return result

    # --- book token (may be multi-word like "1 Samuel") ---
    book_token = tokens.pop(0)
    if book_token.isdigit() and tokens:
        book_token = book_token + tokens.pop(0)

    book_key = book_token.lower().replace(" ", "")
    if book_key not in BOOK_ALIASES:
        result["error"] = f"Unknown book: '{book_token}'. Try an abbreviation like Gen, Exo, Matt."
        return result
    result["book"] = BOOK_ALIASES[book_key]

    # --- optional ref token: chapter:verse, chapter:verse-range, or bare chapter ---
    if tokens:
        next_token = tokens[0]
        next_lower = next_token.lower()

        # full verse ref: 1:1 or 1:1-5
        ref_match = re.match(r"^(\d+):(\d+)(?:-(\d+))?$", next_token)
        if ref_match:
            tokens.pop(0)
            result["chapter"] = int(ref_match.group(1))
            result["verse_start"] = int(ref_match.group(2))
            if ref_match.group(3):
                result["verse_end"] = int(ref_match.group(3))

        # bare chapter integer (not a mode/translation/style keyword)
        elif (next_token.isdigit()
              and next_lower not in MODES
              and next_lower not in CROSS_STYLES
              and next_lower not in TRANSLATIONS):
            tokens.pop(0)
            result["chapter"] = int(next_token)

        # otherwise leave chapter/verse as None (book-scope)

    # --- remaining tokens: mode, word, cross_style, translation ---
    for token in tokens:
        lower = token.lower()
        if lower in MODES:
            result["mode"] = lower
        elif lower in CROSS_STYLES:
            result["cross_style"] = lower
        elif lower in TRANSLATIONS:
            result["translation"] = lower.upper()
        else:
            result["word"] = token

    # modes that require a full verse ref
    if result["book"] and result["verse_start"] is None:
        if result["mode"] == "cross":
            result["error"] = (
                "Cross mode requires a verse reference. "
                "Example: byble Gen 1:1 Cross"
            )
        # book-only Exeg is valid — shows book introduction
        elif result["mode"] is None and result["chapter"] is None:
            result["error"] = "Missing chapter or chapter:verse. Example: byble Gen 1  or  byble Gen 1:1"

    return result
