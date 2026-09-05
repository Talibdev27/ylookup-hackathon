# Statements → journal entries, with a review queue

Fund administrators turn bank statements into journal entries by hand. The working file
we were given shows what that costs: of 100 transaction rows, **52 have no counterparty
match at all**, 30 project codes do not resolve, and 3 rows are simply flagged `Review`.

From the interview transcript, a fund manager on the same problem:

> "From a quality control perspective there just is not any. I do not think it even needs
> frontier-level intelligence to catch. Frankly I no longer read what they send. I put it
> through an AI coding tool first, and it produced a forty-point memo of what was wrong."

So this does the work **and shows its evidence**. The agent proposes a counterparty, a
project code and a classification for every row; the reviewer sees the proposal, its
confidence, and the exact span of bank narrative it came from, and approves or corrects it.

## Using it on your own data

The app opens on the sample dataset. To work on real statements, go to **Load new
statements** and upload:

1. **This week's bank statements** — one PDF per account, as many as you like.
2. **Your reference lists** — the Excel workbook holding your funds, related parties,
   investors, suppliers and deals. Uploaded once; only re-uploaded when they change.

Both halves resolve independently, so the weekly job is just dropping in the PDFs.

The matcher is worthless without the reference lists — without them it can read the
statements but cannot tell you who anyone is — so the upload screen says so rather than
quietly producing a hundred rows of "no answer found".

Scoring is skipped for uploaded data: `Staging Sheet` holds *the human's answers*, and
real client data has no answer key.

## Run it

```bash
./run.sh
```

That installs dependencies, builds the data spine, and prints the score against the
100 human-graded ground-truth rows. Then:

```bash
python3 serve.py
```

Point `YLOOKUP_DATA` at the dataset directory if it is not in `~/Downloads`.

## Where every number on screen comes from

Nothing is asserted without a source. Each row in the review queue carries its own
provenance, because "can you show us where it came from" is the question being asked.

| On screen | Source |
|---|---|
| Account, date, amount, bank text | The statement PDF, named with its page number on every row |
| Highlighted text inside the bank narrative | Character offsets into the raw narrative, carried on every field as `evidence.span` |
| "Why we are asking" | The `Process` sheet in the client's workbook, cited by stage |
| Counterparty, project, deal | The workbook master lists, cited by list name |
| The scoreboard | `Staging Sheet` -- the human's own 100 answers |

## How it is scored

`python -m src.matcher.score` reports two different numbers per field, because they
answer different questions:

- **agreement** — of the rows the human filled, how many do we reproduce exactly?
- **net new** — of the rows the human left blank, how many do we resolve?

## Layout

| Path | Owner | What |
|---|---|---|
| `src/contract.py` | shared | The row shape. Read `CONTRACT.md` before touching it. |
| `src/pipeline.py` | — | Run the whole thing: `run(workspace) → PipelineResult` |
| `src/spine/` | W1 | Reads the workbook and the statement PDFs |
| `src/matcher/` | W2 | The Process-sheet stages, `ReferenceLists`, and `score.py` |
| `src/ui/` | W3 | Exception-first review queue |
| `src/journal/` | W4 | Stage 6: two DIU lines per Batch ID |
| `docs/` | all | One brief per workstream |

## Requirements

Python 3.9+. Dependencies in `requirements.txt`. Note the target is 3.9, so modules use
`from __future__ import annotations` and avoid `match` statements.

## Data notes

The workbook has three traps, all of which fail silently. `src/spine/xlsx.py` handles
them; anything else reading the file must too.

1. **Blank cells are omitted from the sheet XML.** Positional reads shift every later
   column left. Cells must be placed by their `r=` reference.
2. **Text is XML-escaped**, including the sheet names themselves — the deal master is
   stored as `Deal &amp; Position Master List`.
3. **Dates are Excel serials** (`46112` = 2026-03-05), epoch 1899-12-30.

And one that is not a bug: the sheet named `"DIU "` has a **trailing space**.
