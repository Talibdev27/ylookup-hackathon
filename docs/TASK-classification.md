# Task · `classification` and `counterparty_transtype`

> **Done — 5 September.** Both stages are written and in `REGISTRY`. `classification`
> scores **93/100**, `counterparty_transtype` **92/100**. Kept as the record of how they
> were approached and what was measured on the way; the remaining misses are accounted
> for row by row in `where-the-points-go.md`. Nothing below is outstanding work.

Two columns, filled on all 100 ground-truth rows, both scoring 0/100 when this was
written. Together they were the largest block of unclaimed score. You work in one file,
`src/matcher/stages.py`, so nobody else is in your way.

Read `AGENTS.md` first — it has the conventions and the loop. Then work these steps in
order. Each one ends on something you can check, and each one is a commit.

---

## Step 0 · Get a baseline

```bash
git clone https://github.com/Talibdev27/ylookup-hackathon.git
cd ylookup-hackathon
pip3 install -r requirements.txt
./run.sh
```

The dataset needs to be at `~/Downloads/Ylookup Hackathon Datasets/`, or set
`YLOOKUP_DATA` to wherever you put it.

Save the scoreboard `./run.sh` prints. Every later step is measured against it, and two
of its rows are yours:

```
classification                             0/100      0          0/0
counterparty_transtype                     0/100      0          0/0
```

**Done when** `./run.sh` prints a scoreboard and `./run-tests.sh` is green on a clean
clone.

---

## Step 1 · `classification`, the free rules

The ground truth splits seven ways. **The vocabulary is not what the `Process` sheet
claims** — it says "Investment, Vendor, Related Party, Investor, Internal, or Review", but
there is no `Investor`, and `Other` and `Investment Transfer` both appear. Trust the data.

| Count | Value |
|---:|---|
| 32 | `Other` |
| 17 | `Internal` |
| 15 | `Investment Transfer` |
| 15 | `Investment` |
| 12 | `Related Party` |
| 6 | `Vendor` |
| 3 | `Review` |

The shortcut: classification tracks **which reference list the counterparty matched
against**, and the matcher already records that in
`row.fields["matched_sender_beneficiary"].evidence.source_list`. Measured on current
output:

| Matched in | Classification | Hit rate |
|---|---|---|
| `Deal & Position Master List` | `Investment` | 6 / 6 |
| `Investor Master List` | `Related Party` | 5 / 5 |
| `Vendor Master List` | `Vendor` | 6 / 7 |
| `Related Party Master` | splits four ways | step 2 |
| no match at all | `Other` 32, `Internal` 10, `Investment Transfer` 9 | step 2 |

Write those three rules and nothing else. `matched_sender_beneficiary` runs before you in
`REGISTRY`, so read its field rather than recomputing it. Everything you cannot decide
yet returns `status="needs_review"` with an honest `evidence.text`.

**Done when** `classification` scores at least 15/100 and no other row on the scoreboard
has moved. Commit.

---

## Step 2 · `classification`, the residue

52 rows have no counterparty match at all and split `Other` 32, `Internal` 10,
`Investment Transfer` 9, `Review` 3 (approximately — check it yourself). 23 more matched
against `Related Party Master` and split four ways.

The narrative is your evidence. `INTERNAL TRANSFER` is the obvious handle for `Internal`;
find the rest by reading rows rather than guessing at them:

```bash
python3 - <<'EOF'
from src.spine.build import load_workbook
for t in load_workbook()["Staging Sheet"]:
    if t["Classification"] == "Internal":
        print(" ".join(t["Narrative"].split())[:110])
EOF
```

`Other` is the majority class, so it is the sane fallback — but a fallback returns
`needs_review`, not `auto`. Guessing `Other` confidently on 32 rows scores well and lies
to the reviewer.

**Done when** `classification` is above 55/100 and every value you emit is one of the
seven real ones. Commit.

---

## Step 3 · `counterparty_transtype`, the bank charges

The account the counterpart line books to.

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
| 5 | `Investments - Loan - Purchase` |
| 5 | `Income - Bank Interest` |
| 5 | `Receivable - Related Party` |
| 4 | `Suspense (debit)` |

**26 of 100 are bank charges**, and those rows say so in the narrative — `CHARGES FOR`,
`CHARGE WAIVED`. `CREDIT INTEREST` is `Income - Bank Interest`. That is a third of the
column from narrative keywords.

The `CoA` sheet holds the 560-row chart of accounts; reach it through
`ReferenceLists` if you want to check a value you are about to emit actually exists.
Rows the `Process` sheet says to book to Suspense are the ones it asks a reviewer to
investigate, so those are `needs_review` by definition.

**Done when** `counterparty_transtype` is above 30/100. Commit.

---

## Step 4 · `counterparty_transtype`, the rest

Register after `classification` and its field is available to you on `row.fields`. The
`Investments - …` and `… - Related Party` values clearly track it, and `Currency
Correcting Debit` / `Credit` track the direction of the amount.

**Done when** the number stops moving on two consecutive attempts. Then stop and tell the
team — there is more score in `matched_project_code` (100 rows filled, 30 of them the
literal string `Flag for review - no project match`) than in grinding the last few here.

---

## Step 5 · Tests, then push

Add cases to `tests/test_stages.py` beside the existing ones. There is a three-line fake
`ReferenceLists` at the top, so a stage test needs no workbook and runs instantly.

Cover, for each of your two stages: one row it gets right, and one row it should hand to
the reviewer.

```bash
./run-tests.sh   # green
./run.sh         # your two rows up, every other row unchanged
git push
```

**Done when** both are true and the push lands on `main`.

---

## The one rule that matters

**Measure after every change.** If a number drops, revert — the reasoning that convinced
you was wrong, and finding out why costs more than it returns. `complete()` in
`src/matcher/counterparty.py` carries three implementations measured against each other,
where the cleverest scored 7/55 against the simplest at 37/55. That comment exists so the
next person does not spend the hour again.
