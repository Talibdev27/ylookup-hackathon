# Statements → journal entries, with a review queue

Fund administrators turn bank statements into journal entries by hand. The working file
we were given shows what that costs: of 100 transaction rows, **52 have no counterparty
match at all**, 30 project codes do not resolve, and 3 rows are simply flagged `Review`.

From the interview transcript, a fund manager describing his own administrator:

> "From a quality control perspective there just is not any. I do not think it even needs
> frontier-level intelligence to catch. Frankly I no longer read what they send. I put it
> through an AI coding tool first, and it produced a forty-point memo of what was wrong."

> "Which raises the question of whether I should be building software to check my own fund
> administrator."

**This is that software.**

It is not built to be fast, because speed is not what he asked for:

> "As a user I am not sensitive to whether a turn took them an hour or forty-eight hours.
> What I care about is the count of turns. That is the drag on my time."

A turn is spent when something comes back wrong. So this does the work **and shows its
evidence**, because the way to cut turns is to make every answer checkable before it goes
back — he checks everything today only because he cannot tell which numbers are safe.

Ten matcher stages propose a counterparty, a project code, a deal, a position and a
classification for every row. Automated checks then look for inconsistencies such as a
broken running balance. The reviewer sees both kinds of work in one queue, with the
proposal or finding, its reason, and the statement source, and can approve, correct,
acknowledge, resolve, or say the machine is right to be unsure.

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

| Column | agreement | net new |
|---|---|---|
| **Fund** · `matched_legal_entity` | 100/100 | — |
| **Cash side of the entry** · `cash_leg_transtype` | 100/100 | — |
| **Project mentioned** · `pulled_out_project_code` | 25/25 | 0/75 |
| **Type of transaction** · `classification` | 98/100 | — |
| **Project code** · `matched_project_code` | 99/100 | — |
| **Other side of the entry** · `counterparty_transtype` | 98/100 | — |
| **Name in the bank text** · `pulled_out_sender_beneficiary` | 53/55 | 45/45 |
| **Counterparty** · `matched_sender_beneficiary` | 45/48 | 8/52 |
| **Deal** · `resolved_deal` | 26/30 | 0/70 |
| **Position** · `resolved_position` | 26/30 | 0/70 |

A dash under *net new* means the human left nothing blank in that column, so there was
nothing for us to resolve.

A column's misses are not all defects. **Counterparty** is the hardest column on the sheet
and now disagrees with the human on **nothing**: the three rows it does not reproduce are
three it declines, because they name a group entity by an in-house alias that appears
nowhere in the workbook. Across all ten columns there are seven disagreements in total.

Of the rest, eight rows want an answer the statement and the reference data do not contain,
and five are contradictions in the client's own file — including three booked to a deal
that exists in no master list. Every missing point is accounted for row by row in
[`docs/where-the-points-go.md`](docs/where-the-points-go.md).

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
rejected.

The same transaction card also carries any automated inconsistency findings. Six checks
run today — balance continuity, duplicate transactions, round-number amounts, currency
mismatches, journal batch integrity, and reference-list quality — see
[`docs/analyst-flags.md`](docs/analyst-flags.md) for what each looks for and its real
finding on the sample data. Each finding has a stable ID, severity, plain-English
explanation, expected and actual values, and its statement page. A reviewer can
acknowledge it, mark it resolved, or mark it as a false positive, with an optional note.
Matcher answers and check actions are stored separately and both travel with the CSV export.

The sample data produces 35 findings across those six checks — 24 round-number amounts and
11 near-duplicate reference-list name pairs, both `severity="info"`/`"review"` rather than
errors, and genuine negatives everywhere else (the statements foot, nothing duplicates, no
currency is out of place, every journal batch balances). The page reports the count after
recording that every check ran; a clean result on any individual check is never presented
as a skipped one. Long proposed position values use a short preview with an accessible
expand/collapse control, while the complete value remains available to decisions and export.

A separate frontend can consume `GET /api/review` and submit automated-flag decisions to
`POST /api/flags/<flag_id>/decide`. The full schemas and screen-state guidance are in
[`docs/FRONTEND-HANDOFF.md`](docs/FRONTEND-HANDOFF.md).

`GET /api/gl-migration/flags` covers a second, unrelated dataset — the investor-level GL to
loader upload (`src/gl_migration/`) — with its own five checks and 220 real findings. See
[`docs/analyst-flags.md`](docs/analyst-flags.md) §3.

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
- **net new** — of the rows the human left blank, how many do we fill in?

Two things these numbers do not say, spelled out because they are the first things a
careful reader will ask:

**Net new measures coverage, not accuracy.** A row the human left blank has no answer key
— that is why it is blank — so nothing checks the value we put there. Any answer counts.
Read `45/45` as "we produced a name on all 45", never as "we got 45 right".

**A row can land in neither number.** If the human filled a cell and we return no answer,
it counts as neither agreement nor a disagreement, because declining to guess is not the
same as guessing wrong. So the agreement and wrong counts do not add up to the rows the
human filled — on **Counterparty** the 45 agreements and 0 disagreements come to 45 of 48,
and the missing three are rows we handed to a reviewer.

## Layout

See `docs/ARCHITECTURE.md` for how these actually connect, stage by stage.

| Path | What |
|---|---|
| `run.sh` | The feedback loop: build the spine, run every stage, print the scoreboard |
| `run-tests.sh` | Every suite, exiting non-zero on the first failure |
| `serve.py` | Starts the review queue |
| `src/contract.py` | The row shape every stage reads and writes. `CONTRACT.md` explains it |
| `src/pipeline.py` | Runs the whole thing: `run(workspace) → PipelineResult` |
| `src/spine/` | Reads the reference workbook and the statement PDFs |
| `src/matcher/` | The ten Process-sheet stages, `ReferenceLists`, and `score.py` |
| `src/ui/` | The exception-first review queue, and the wording it puts on screen |
| `src/exporter.py` | The reviewed queue as a spreadsheet, carrying matcher answers, check findings and reviewer decisions |
| `src/extraction/` | Document-agnostic PDF reading, with a Tesseract OCR fallback for a page with no text layer |
| `src/checks/` | Registry, runner and six automated inconsistency checks over already-structured records — see `docs/analyst-flags.md` |
| `src/gl_migration/` | A separate analyzer for the investor-level GL → loader dataset, exposed at `GET /api/gl-migration/flags` |
| `src/reports/` | Balance sheet and income statement, rolled up directly from the `DIU`/`CoA` sheets — not the matcher's output |
| `src/storage/` | Versioned SQLite archive of uploaded workbooks, extracted PDF pages and current check findings |
| `tests/` | All suites, run together by `./run-tests.sh`. `tests/test_stages.py` carries a three-line fake `ReferenceLists`, so testing a stage needs no workbook |
| `docs/` | The architecture, the roadmap, and the decision records. `counterparty-matching.md` and `deal-resolution.md` cover how the hard columns work and what was measured and rejected getting there; `where-the-points-go.md` accounts for every point the scoreboard does not give us; `FRONTEND-HANDOFF.md` is the JSON API contract for a separate frontend; `backend-integration.md` covers the `truss/` Next.js app that actually consumes it |
| `truss/` | A Next.js frontend, three of its pages wired to the real backend above — see `docs/backend-integration.md` |

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
