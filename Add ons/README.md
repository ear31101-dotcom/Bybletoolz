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
