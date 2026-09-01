# Add-ons

This folder contains documentation for importing exegetical commentary into Bybletoolz for use with the `Exeg` study mode. Personal commentary files are stored locally in `Commentary Library (gitignore)/` and are not tracked by git.

---

## Commentary Library

The `Commentary Library (gitignore)/` subfolder holds CSV files for import. It is gitignored — its contents never appear on GitHub.

Place any commentary CSVs there and import with:

```bash
byble import exeg "Add ons/Commentary Library (gitignore)/<file>.csv" "Source Name"
```

---

## Supported Sources

### OT Commentary — Advanced Structured CSV

**Coverage:** Genesis through Malachi (39 books)  
**Format:** Advanced Structured CSV  
**Includes:** Verse notes, book introductions, thematic articles

Notes are organized by verse range with cross-chapter scope support (e.g. Genesis 1:1–11:26). Includes book-level introductions for each OT book and standalone thematic articles browsable via `byble exeg`.

```bash
byble import exeg "Add ons/Commentary Library (gitignore)/ot_commentary.csv" "OT Commentary"
```

---

### NT Commentary — Advanced Structured CSV

**Coverage:** Matthew through Revelation (27 books)  
**Format:** Advanced Structured CSV  
**Includes:** Verse notes, book introductions, thematic articles

```bash
byble import exeg "Add ons/Commentary Library (gitignore)/nt_commentary.csv" "NT Commentary"
```

---

### SDA Bible Commentary — Advanced Structured CSV

**Full title:** Seventh-day Adventist Bible Commentary  
**Publisher:** Review and Herald Publishing Association (1953–1957)  
**Coverage:** Full Bible (Genesis through Revelation)  
**Format:** Advanced Structured CSV

The classic multi-volume SDA commentary. Notes are verse-anchored and include Ellen G. White cross-references alongside standard exegetical content.

```bash
byble import exeg "Add ons/Commentary Library (gitignore)/sda_bible_commentary.csv" "SDA Bible Commentary"
```

---

## Adding Your Own Sources

Any CSV or e-Sword `.cmtx` file can be imported. See [`CSV_IMPORT_GUIDE.md`](CSV_IMPORT_GUIDE.md) for how to structure CSV data.

```bash
byble import exeg "Add ons/Commentary Library (gitignore)/my_source.csv" "My Commentary"
byble import list
```

---

## Viewing Imported Commentary

```bash
byble Gen Exeg          # Book introduction
byble Gen 1 Exeg        # Full chapter notes
byble Gen 1:1 Exeg      # Single verse
byble Gen 1:1-5 Exeg    # Verse range
byble exeg              # Browse standalone articles across all sources
```
