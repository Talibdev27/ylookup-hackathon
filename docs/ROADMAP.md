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
`src/spine/pdf.py` is the statement parser built over it. **No sample balance sheet,
income statement or cash flow PDF exists in the hackathon dataset**, and that has not
changed — a new PDF-sourced document type still gets its own parser over the same
primitive rather than its own PDF-reading code, whenever one turns up.

What changed: a balance sheet and income statement exist today anyway, without a PDF —
`src/reports/statements.py` rolls them up directly from the `DIU` and `CoA` sheets already
in the reference workbook, real posted journal lines, not a new document type at all. See
`docs/ARCHITECTURE.md` §5a. Cash flow has no equivalent shortcut: the data has nothing that
maps to operating/investing/financing activities, so it stays open.

Dataset 02 (investor-level GL → loader) remains real, present, and untouched by any code
here — 34,000 source rows across 43 columns, four crosswalks, and a 19,000-row output —
the gradeable target if a genuinely new document type is wanted rather than a rollup of
data already on hand.

## More checks

`src/checks/` runs after extraction over already-structured records, asking *does this add
up?* rather than *what is this?* — a different job from the matcher. `footing.py` is the
first: balance continuity, one `Flag` per row where a statement's running balance does not
follow from the row before it in the same account. The check is now part of the normal
pipeline: its execution status and findings are persisted, shown in the unified review
queue, available through the frontend JSON API, and included in the reviewed export.

It currently finds nothing on the sample data, which is the correct answer — those
statements do foot. Future checks worth adding are the ones that would have caught the
interview's complaints: a subsequent event whose date was rolled forward rather than moved,
and a side-letter fee calculation that does not tie.

"A balance sheet with no bridge to the equity balance," listed here originally, is now
partly answered: `src/reports/statements.py`'s `ties()` checks the expanded accounting
equation on every balance sheet request, but as a boolean on the API response, not a
`Flag` a reviewer acts on in the queue. Wiring it into `src/checks/` properly is still open.

## A front door

**Built, 5 September** — a band at the top of the queue (`review.html`'s `.intro`
section), not a separate landing page: two sentences on what the tool is, the
Process-sheet finding count, and a link to the video when `YLOOKUP_VIDEO_URL` is set.
Deliberately not a hero animation or a route change — the scoring rubric's UI criterion
reads "Clean and considered... No AI slop," and moving the queue to make room for a
landing page would have changed the URL the demo was filmed against.

The wider version of this is still open: a landing step that takes a folder of documents,
says what it found in each, and hands the reviewer a queue per document rather than one
flat list across every fund. `truss/`'s Company Workspace (`docs/backend-integration.md`)
is the real version of this now — a per-fund Review Queue tab, Balance Sheet, Income
Statement and Cash Flow, backed by `GET /api/companies` — so the open piece left here is
folding a document-upload step into that experience, not building a landing page for the
Flask-only queue a second time.
