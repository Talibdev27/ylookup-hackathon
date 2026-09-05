# W1 · Data spine + ETL

**Deliverable:** `python -m src.pipeline` produces `data/rows.json` in under 60 seconds
from a clean checkout. `src/spine/` is the loading half; `src/pipeline.py` owns the order
the steps run in.

## Job

1. Parse the 7 PDFs in `01-.../statements/` into transaction rows. Filenames encode
   entity, bank, currency and account short code — parse them, do not hardcode. Four
   currencies (EUR, USD, GBP, DKK), six business days. `src/spine/pdf.py` has the
   filename regex; the PDF body is yours.
2. Load all 15 workbook sheets. **Already done** — `load_workbook()` works and asserts on
   row counts for the sample. (An earlier version also dumped them to SQLite; nothing read
   it, so it was deleted.)
3. Emit `rows.json` in the `CONTRACT.md` shape with `fields` empty. W2 fills them,
   W3 renders them.

## Gotchas

Handled already in `src/spine/xlsx.py`, listed so you recognise them if they resurface:

- Blank cells are omitted from sheet XML — cells must be placed by `r=` reference.
- Sheet names and cell text are XML-escaped (`Deal &amp; Position Master List`).
- Dates are Excel serials, epoch 1899-12-30. `serial_to_date()` is there.
- The sheet `"DIU "` has a trailing space.

The one still ahead of you: **narratives wrap mid-word with commas at the wrap points.**
Keep the wrapped original as `narrative_raw` — the review UI highlights evidence spans
that index into it. `normalise()` returns an index map for exactly this.

## Done when

W2 and W3 can both import real data and never open an `.xlsx` or a PDF again.
