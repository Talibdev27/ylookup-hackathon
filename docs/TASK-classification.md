# Task · `classification` and `counterparty_transtype`

Two columns, both filled on all 100 ground-truth rows, both currently scoring **0/100**.
Self-contained: you work in one file and nobody else needs to touch it.

## Get running (5 minutes)

```bash
git clone https://github.com/Talibdev27/ylookup-hackathon.git
cd ylookup-hackathon
pip3 install -r requirements.txt
./run.sh
```

You need the dataset in `~/Downloads/Ylookup Hackathon Datasets/`, or set `YLOOKUP_DATA`
to wherever it is. `./run.sh` prints the scoreboard. That number is your target.

## What you are writing

Two functions in `src/matcher/stages.py`. Both already exist as stubs that raise
`NotImplementedError` — replace the body, nothing else.

```python
def classification(row: Row, lists: ReferenceLists) -> Field: ...
def counterparty_transtype(row: Row, lists: ReferenceLists) -> Field: ...
```

Every stage has that shape. Copy `matched_legal_entity` or `cash_leg_transtype` — they are
short, implemented, and show the conventions: always return a `Field` with a `confidence`,
a `status`, and an `Evidence` saying where the answer came from. **Never return a bare
value.** A field with no evidence cannot be reviewed, and the review screen renders
`evidence.text` to a fund manager, so write it in their language.

Then: `./run.sh` and watch your two rows on the scoreboard.

## `classification` — the head start

The ground truth splits seven ways:

| Count | Value |
|---:|---|
| 32 | `Other` |
| 17 | `Internal` |
| 15 | `Investment Transfer` |
| 15 | `Investment` |
| 12 | `Related Party` |
| 6 | `Vendor` |
| 3 | `Review` |

**Note the vocabulary is not what the docs say.** The `Process` sheet claims it is
"Investment, Vendor, Related Party, Investor, Internal, or Review". The data says
otherwise — there is no `Investor`, and `Other` and `Investment Transfer` both appear.
Trust the data.

**The big shortcut:** classification correlates strongly with *which reference list the
counterparty matched against*, and the matcher already records that in
`row.fields["matched_sender_beneficiary"].evidence.source_list`. Measured on the current
output:

| Matched in | Classification | Hit rate |
|---|---|---|
| `Deal & Position Master List` | `Investment` | 6 / 6 |
| `Investor Master List` | `Related Party` | 5 / 5 |
| `Vendor Master List` | `Vendor` | 6 / 7 |
| `Related Party Master` | splits 4 ways | needs the narrative |
| no match at all | `Other` 32, `Internal` 10, `Investment Transfer` 9 | needs the narrative |

So roughly 17 rows are three `if` statements. The rest needs narrative keywords —
`INTERNAL TRANSFER` is the obvious one for `Internal`. Start with the free ones, commit,
then work the residue. Do not try to be clever before the scoreboard moves.

`matched_sender_beneficiary` runs before you in `stages.REGISTRY`, so its field is already
on `row.fields` when your stage is called. Read it, don't recompute it.

## `counterparty_transtype` — the head start

The account the counterpart line books to. Top values:

| Count | Value |
|---:|---|
| 26 | `Expense - Bank Charges` |
| 10 | `Investments - Equity - Purchase` |
| 9 | `Payable - Third Party` |
| 8 | `Currency Correcting Debit` |
| 7 | `Payable - Related Party` |
| 7 | `Accounts Payable` |
| 6 | `Currency Correcting Credit` |
| 6 | `Receivable` |

**26 of 100 are bank charges**, and those rows are recognisable from the narrative
(`CHARGES FOR`, `CHARGE WAIVED`, `CREDIT INTEREST`). That alone is a quarter of the column.
The `CoA` sheet holds the full 560-row chart of accounts if you want to validate that a
value you are about to emit actually exists.

`row.fields["classification"]` is available to you if you register after it — the
`Investments - Equity - Purchase` and `Payable - Related Party` values clearly track it.

## Rules of the road

- **Measure, don't guess.** After every change run `./run.sh`. If a number goes down,
  revert. Three of us have already lost time to a change that looked obviously better and
  scored worse — the reasoning is recorded in `complete()` in `src/matcher/counterparty.py`
  if you want the example.
- **Run `./run-tests.sh` before you push.** It exits non-zero on the first failure.
- **Add a test in `tests/test_stages.py`.** There is a three-line fake `ReferenceLists` at
  the top; you do not need the real workbook to test a stage.
- **Unsure is a valid answer.** `status="needs_review"` with an honest `evidence.text` is
  worth more than a confident wrong value. The whole product is about being told when the
  machine is not sure.

## Read first

`CONTEXT.md` for the vocabulary, then `docs/W2-matcher.md`. Both are short.
