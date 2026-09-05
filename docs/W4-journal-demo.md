# W4 · Journal builder + demo + integration

**Deliverable:** the submission actually lands.

## 1. Stage 6 — the journal

Verified against the real DIU sheet: 29 columns, 200 lines, 100 batches. Column list and
the worked example are in `src/journal/build.py`.

The pair for one batch shares `Batch ID` and `JE Index`, splits on `is Debit` (Yes/No)
with `Trans Index` 1 and 2, carries the same `Amount (Local)`, and shares a
`Transaction Reference` composite key `{date_serial}_{amount}_{ccy}` — e.g.
`46112_0.44_EUR`. That key is also how you join back to the staging row, so use it to
verify the pairing rather than trusting row order.

## 2. The one command

Minimum bar is a README plus one command the judges can execute. `./run.sh` exists —
**test it on a clean clone**, not on your machine with your half-remembered environment.

## 3. The video (3–5 min)

Open with the problem and the interview quote it came from — that is literally the first
scoring criterion. Then show the product working. Script it; do not improvise on Sunday
morning.

## 4. Own the clock

- **Saturday 20:00** — if statements → journal entries is not running end to end with the
  review UI, dataset 02 is abandoned permanently.
- **Sunday 09:00** — code freeze. 09:00–11:00 is README, video and Tally.
- **Sunday 11:00** — submit, with an hour of slack. Resubmission is allowed, so there is
  no reason to be submitting at 11:58.

## 5. The interview

Come back with one quotable sentence for the video's opening, and the judges' view on
which dataset they consider the harder problem.
