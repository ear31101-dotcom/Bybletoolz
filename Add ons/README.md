# Add-ons

This folder contains exegetical commentary sources that can be imported into Bybletoolz for use with the `Exeg` study mode.

---

## Included Sources

### OT Commentary (Advanced Structured CSV)

**Coverage:** Genesis through Malachi (39 books)  
**Format:** Advanced Structured CSV (see import guide)

An academic commentary on the Old Testament. Notes are organized by verse range and include book-level introductions for each OT book. Coverage includes exegetical analysis, historical background, literary structure, and theological themes. Cross-chapter note ranges are preserved (e.g. Genesis 1:1–11:26).

**Import command:**
```bash
byble import exeg "Add ons/<your_file>.csv" "OT Commentary"
```

---

### SDA Bible Commentary (`sda_bible_commentary.csv`)

**Full title:** Seventh-day Adventist Bible Commentary  
**Publisher:** Review and Herald Publishing Association (1953–1957)  
**Coverage:** Full Bible (Genesis through Revelation)  
**Format:** Advanced Structured CSV (see import guide)

The classic multi-volume SDA commentary covering the entire Bible. Notes are verse-anchored and include Ellen G. White cross-references alongside standard exegetical content. Coverage varies by book — some books have dense verse-by-verse notes while others are lighter.

**Import command:**
```bash
byble import exeg "Add ons/sda_bible_commentary.csv" "SDA Bible Commentary"
```

---

## Adding Your Own Sources

You can import additional commentary sources in CSV or XLSX format. See [`CSV_IMPORT_GUIDE.md`](CSV_IMPORT_GUIDE.md) for how to structure the data.

```bash
byble import exeg "Add ons/my_source.csv" "My Commentary"
byble import list
```

---

## Viewing Imported Commentary

```bash
byble Gen Exeg              # Book introduction
byble Gen 1 Exeg            # Full chapter notes
byble Gen 1:1 Exeg          # Single verse
byble Gen 1:1-5 Exeg        # Verse range
```
