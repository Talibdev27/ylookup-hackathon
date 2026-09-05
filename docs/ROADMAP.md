# Where this goes next

The weekend's build is statements → reviewable journal entries. This is the work beyond
it, kept in one place so the repo shows the direction without implying half-finished
tasks.

## Stage 6 · Journal entries out

The matcher fills the staging row; turning it into the target system's upload format is
the step after. Verified against the real DIU sheet: 29 columns, 200 lines, two per
Batch ID.

`Legal Entity` · `Transaction Type` · `Legal Entity Domain` · `Deal Name` · `Position` ·
`Batch ID` · `JE Index` · `Trans Index` · `GL Date` · `Effective Date` ·
`Transaction currency` · `Allocation Rule` · `Trans Type Sub Category` · `is Debit` ·
`Amount (Local)` · `Amount (LE)` · `Quantity` · `Transaction Comments` · `Related Party` ·
`CostName` · `ReasonName` · `Transaction GL Reference` · `Batch Comments` · `Bank Account` ·
`Comments 2` · `Transaction Reference` · `Vendor` · `Account ` · `Project Code`

A worked example — batch 1, a EUR bank charge of 0.44:

| | line 1 | line 2 |
|---|---|---|
| Transaction Type | `Cash - Disbursed - EUR` | `Expense - Bank Charges` |
| is Debit | `No` | `Yes` |
| Allocation Rule | `Non Dominant` | `No Allocation` |
| Trans Index | 2 | 1 |
| Transaction Reference | `46112_0.44_EUR` | `46112_0.44_EUR` |

The pair shares `Batch ID` and `JE Index`, splits on `is Debit`, carries the same
`Amount (Local)`, and shares a `Transaction Reference` of `{date}_{amount}_{ccy}` — which
is also the join key back to the staging row, so it verifies the pairing rather than
trusting row order.

## A second document type

`src/extraction/pdf_text.py` reads any PDF into page text and page tables;
`src/spine/pdf.py` is the statement parser built over it. A new document type — a balance
sheet, an income statement, a cash flow — gets its own parser over the same primitive
rather than its own PDF-reading code.

**No sample of those documents exists in the hackathon dataset.** Until one does, the
gradeable target is dataset 02 (investor-level GL → loader), which is real, present, and
much larger: 34,000 source rows across 43 columns, four crosswalks, and a 19,000-row
output.

**A second extraction path, for documents `pdfplumber` reads badly.** Bank statements are
clean, machine-generated tables — `pdfplumber` reads them well, which is why
`matched_legal_entity` and `cash_leg_transtype` hit 100/100. A scanned or multi-column
financial statement is a different problem. `marker_service/` wraps
[Marker](https://github.com/datalab-to/marker) — layout-aware, deep-learning extraction —
as its own deployment, because it needs Python 3.10+ and PyTorch, neither of which the
main app's Python 3.9 target or single Render-free-tier worker can carry.
`src/extraction/marker_client.py` is the one place the main app knows this service
exists: a thin HTTP call, gated entirely on `MARKER_SERVICE_URL` being set, so the app
runs exactly as it does today with the service turned off. See
`marker_service/README.md` for what it costs to actually deploy and run this — it is not
free compute, and it is not fast on a cold start even with model weights baked into the
image.

## More checks

`src/checks/` runs after extraction over already-structured records, asking *does this add
up?* rather than *what is this?* — a different job from the matcher. `footing.py` is the
first: balance continuity, one `Flag` per row where a statement's running balance does not
follow from the row before it in the same account.

It currently finds nothing on the sample data, which is the correct answer — those
statements do foot. The checks worth adding next are the ones that would have caught the
interview's complaints: a subsequent event whose date was rolled forward rather than moved,
a side-letter fee calculation that does not tie, a balance sheet with no bridge to the
equity balance.

## A front door

The review queue assumes you already know what you are looking at. A landing step would
take a folder of documents, say what it found in each, and hand the reviewer a queue per
document rather than one flat list.
