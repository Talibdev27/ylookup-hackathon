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
a side-letter fee calculation that does not tie, a balance sheet with no bridge to the
equity balance.

## A front door

The review queue assumes you already know what you are looking at. A landing step would
take a folder of documents, say what it found in each, and hand the reviewer a queue per
document rather than one flat list.

The narrower version of this is real and near: somebody opening the deployed URL cold --
a judge, a fund manager sent a link -- lands on "Transactions to check" and 88 cards,
with nothing on screen saying what the tool is or whose problem it solves.

**Decided 5 September, and deliberately not built this weekend.** When it is built:

- **A band at the top of the queue, not a landing page.** Two sentences, the 23-row
  finding, a link to the video. Moving the queue to its own route to make room for a
  front page changes the URL the demo is filmed against, and the video was the scarce
  thing that weekend, not the screen.
- **No motion.** The scoring rubric's UI criterion reads "Clean and considered. A
  non-technical fund manager is the user. No AI slop." A tool that looks like a working
  tool is the stronger answer, and the one number worth setting large is the finding
  itself, which does the work a hero animation imitates.
- **Link the video, never embed it.** An embed that fails to load on the judged URL is
  worse than no video section.
