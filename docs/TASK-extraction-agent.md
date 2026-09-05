# Task · Extraction agent — beyond bank statements

The platform's second half: any fund document in, structured records and a workbook out.
`src/extraction/` holds the document-agnostic primitives; `src/spine/pdf.py` is the one
parser built on them so far, specific to bank statements. This is where the next
document types go.

Read `AGENTS.md` and `CONTEXT.md` first. Then work these steps in order.

---

## Step 0 · What already exists

```python
from src.extraction import pdf_text, workbook_writer

document = pdf_text.extract(path)      # -> ExtractedDocument: page text + page tables
workbook_writer.write_workbook(sheets, destination)   # -> {"Sheet name": [records]} -> .xlsx
```

Both are real and tested against the bundled statement PDFs and a round trip through
openpyxl — `tests/test_extraction.py`. Neither is wired into the pipeline yet; that wiring
is this task.

**Done when** `python tests/test_extraction.py` passes on your machine.

---

## Step 1 · The gap this task starts from

There is no sample balance sheet, income statement or cash flow statement anywhere in
`Ylookup Hackathon Datasets/`. Call 1 describes what is wrong with them — a subsequent
event left in with the date rolled forward, a side letter fee miscalculated — but the
organisers did not hand out a PDF of one. Two ways forward, not mutually exclusive:

**(A) Build against real data that does exist.** Dataset 2,
`02-investor-level-gl-to-loader/`, is a second real, anonymised workflow with its own
known gaps already counted in its README (4 unmatched legal entities, 16 unmatched deal
names, 198 unmatched investor names, a populated `Mapping Gaps` sheet). It is closer to
`extraction + checks` over spreadsheet data than PDF data, but it is real and gradeable
today, and it is the honest next step if the weekend runs out before sample statements do.

**(B) Get a real (or realistic synthetic) financial statement PDF.** Ask in the event
Discord whether the organisers or the on-site fund manager have one to hand out, or
construct one deliberately from the numbers already in dataset 1 and 2 (a NAV workbook
naturally implies a balance sheet). Do not invent narrative content that looks anonymised
client data but is not — say plainly in the write-up if a document is synthetic.

**Done when** the team has picked one and said so in the channel — this is a scope
decision, not a solo one, because it changes what the demo can show.

---

## Step 2 · One document type, end to end

Whichever you picked, the shape is the same as `spine/pdf.py`: a parser that turns
`pdf_text.extract()`'s pages into a list of dict records with a stable set of keys, then
`workbook_writer.write_workbook()` to produce the output file. Follow `spine/pdf.py`'s
comments on what to verify (row counts against a known total, or an amount column that
sums to a value stated elsewhere in the document) — an extraction with nothing to check
it against is not trustworthy enough to hand to a fund manager.

**Done when** one document type parses into records, a test pins the row count or an
amount that should sum correctly, and a workbook comes out the other end.

---

## Step 3 · Hand records to the checking agent

`src/checks/` expects structured records, not PDFs — see `docs/TASK-checks-agent.md`.
Once Step 2 produces records, a checking agent can run over them without knowing they
came from a PDF at all. That seam is the point: extraction and checking should not know
about each other's internals.

**Done when** a record from your new parser round-trips through at least one check in
`src/checks/` without a code change on either side.
