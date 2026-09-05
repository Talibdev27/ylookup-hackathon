# Statements → journal entries, with a review queue

Fund administrators turn bank statements into journal entries by hand. The working file
we were given shows what that costs: of 100 transaction rows, **52 have no counterparty
match at all**, 30 project codes do not resolve, and 3 rows are simply flagged `Review`.

From the interview transcript, a fund manager on the same problem:

> "From a quality control perspective there just is not any. I do not think it even needs
> frontier-level intelligence to catch. Frankly I no longer read what they send. I put it
> through an AI coding tool first, and it produced a forty-point memo of what was wrong."

So this does the work **and shows its evidence**. Ten matcher stages propose a counterparty,
a project code, a deal, a position and a classification for every row; the reviewer sees the
proposal, its confidence in words, and the exact span of bank narrative it came from, and
approves, corrects, or says the machine is right to be unsure.

## Try it

- **Live:** <https://ylookup-hackathon.onrender.com/>
  *(free tier — it sleeps after 15 minutes, so the first load takes 30–60 seconds)*

Or locally, from a clean clone:

```bash
./run.sh          # installs deps, builds the spine, prints the scoreboard (~3s)
python3 serve.py  # the review queue at http://127.0.0.1:5001
```

Point `YLOOKUP_DATA` at the dataset directory if it is not in `~/Downloads`.

## The thing it found that nobody asked it to

The client's workbook ships a `Process` sheet — their own stage-by-stage guide, and the
closest thing to a specification we were given. In three places it describes rules their
own working file does not follow:

| Their rule | Their data |
|---|---|
| Cash leg is `Received` or `Disbursed`, matching the credit or debit side | All 100 rows booked `Cash - Disbursed`, including **the 23 where money came in** |
| Classification is one of six listed values | No `Investor` at all; adds `Other` (32 rows) and `Investment Transfer` (15) |
| Project code is a lookup against the project report | 30 of 100 rows carry the literal string `Flag for review - no project match` |

We reproduce the data so the output stays loadable, and flag the disagreement on every
affected row with the reason in plain English. That is the fund manager's complaint —
*"nobody reads it and asks whether this number foots to that number"* — made concrete on
the administrator's own file, in one run. The reasoning is in
[`docs/adr/0001`](docs/adr/0001-trust-the-data-over-the-process-sheet.md).

## What it scores today

`./run.sh` prints this. Ten of ten columns have a stage behind them; PDF extraction is
100/100 against ground truth.

| Field | agreement | net new |
|---|---|---|
| `matched_legal_entity` | 100/100 | — |
| `cash_leg_transtype` | 100/100 | — |
| `pulled_out_project_code` | 25/25 | 0/75 |
| `classification` | 93/100 | — |
| `matched_project_code` | 92/100 | — |
| `counterparty_transtype` | 92/100 | — |
| `pulled_out_sender_beneficiary` | 45/55 | 45/45 |
| `matched_sender_beneficiary` | 31/48 | 8/52 |
| `resolved_deal` | 25/30 | 0/70 |
| `resolved_position` | 13/30 | 0/70 |

A column's misses are not all defects. `matched_sender_beneficiary` disagrees on fourteen
rows and sends eleven of them to a reviewer rather than booking something wrong.
`resolved_position` reads worst and is not: on 26 of its 30 rows the reviewer gets either
the answer or a short list with the answer on it, because a deal holding several equally
valid positions gets a shortlist instead of a guess. Every missing point is accounted for
row by row in [`docs/where-the-points-go.md`](docs/where-the-points-go.md).

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

## The review queue

Exception-first: rows the matcher is sure about do not ask for attention. On a row that
does, the reviewer can accept the proposal, take one of the alternatives, type a correction
(suggested from the client's own reference lists), or answer **"I can't tell either"** —
which clears the value rather than falling back to a proposal the person has already
rejected. Export is a CSV carrying, per answer, who decided it.

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

See `docs/ARCHITECTURE.md` for how these actually connect, stage by stage.

| Path | Owner | What |
|---|---|---|
| `src/contract.py` | shared | The row shape. Read `CONTRACT.md` before touching it. |
| `src/pipeline.py` | — | Run the whole thing: `run(workspace) → PipelineResult` |
| `src/spine/` | W1 | Reads the workbook and the statement PDFs |
| `src/matcher/` | W2 | The Process-sheet stages, `ReferenceLists`, and `score.py` |
| `src/exporter.py` | — | The reviewed queue as a spreadsheet, with who decided each answer |
| `src/ui/` | W3 | Exception-first review queue |
| `src/extraction/` | — | Document-agnostic PDF reading and Excel output, for document types beyond statements |
| `src/checks/` | — | Automated inconsistency checks over already-structured records |
| `marker_service/` | — | Marker, as its own deployment — needs Python 3.10+ and PyTorch, so it cannot live in `src/`. Off by default; see its README |
| `docs/` | all | Active task briefs, the architecture, the roadmap, the decision records, and `counterparty-matching.md` / `deal-resolution.md` — how the hard columns work, and what was measured and rejected getting there. `where-the-points-go.md` accounts for every point the scoreboard does not give us |

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
