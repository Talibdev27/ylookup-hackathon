# Where the remaining points go

Ten columns, scored against the human's own 100 answers by `./run.sh`. This is the
account of every point not scored, checked row by row against the current output rather
than reasoned about from the code.

| Field | Score | Reason for missing points |
|---|---|---|
| `matched_legal_entity` | 100/100 | — |
| `cash_leg_transtype` | 100/100 | — |
| `pulled_out_project_code` | 25/25 | — |
| `classification` | 93/100 | Four rows lack enough evidence and stay unresolved. Three rows the human labelled `Review` are classified as plausible `Vendor`, `Internal` or `Investment` transactions. |
| `matched_project_code` | 92/100 | Six expected `OVERHEAD` rows are conservatively flagged for review. Two disagree outright: one reads `SARDONYX` out of the narrative where the human flagged the row, and one is an `OH - BOARD MEMBER FE` overhead code with no handle in the bank text. |
| `counterparty_transtype` | 92/100 | Seven of the eight are inherited: the classification behind them is wrong or missing, and this stage is a consequence of it. The eighth is an internal FX row the human books as a credit correction where the amount's direction says debit. |
| `pulled_out_sender_beneficiary` | 45/55 | Nine of the ten are formatting, not identity: a trailing full stop (`NI V KALVIK TOPCO LTD` against `LTD.`), the bank's line-wrap comma (`NORDVIK  INFRASTRUCTURE` against `NORDVIK, INFRASTRUCTURE`), or a name the bank truncated (`S.A R` against `S.A R.L.`). The tenth is a row where the human typed the word `Review` into the name column. |
| `resolved_deal` | 25/30 | Three expect `ZZZ Operations EUR` / `GBP`, which appear nowhere in the deal master. One human answer is a position string in the deal column. One Fenwick row has five deals carrying the project where the human listed four, with no rule visible for the one they dropped. |
| `matched_sender_beneficiary` | 31/48 | Three families. Six rows read `NI ABF II SCSP`, which is on no list, and resolve to the co-invest vehicle where the human chose the full fund. Five want `NIP P/S` where we find another entity of the same group, with nothing in the text separating them. Three are one company under a spelling two sheets disagree about. Eleven of the fourteen go to a reviewer rather than booking through. |
| `resolved_position` | 13/30 | Many deals hold several equally valid positions, and the system returns a shortlist instead of guessing. On 13 further rows that shortlist contains the human's answer, but an exact-match scorer counts it wrong. |

---

## What the scoreboard cannot see

`resolved_position` reads worst and is not the worst. Counted by what a reviewer is
actually handed:

| Outcome | Rows |
|---|---|
| exact answer | 13 |
| shortlist, **and the human's answer is on it** | 13 |
| shortlist, answer not on it | 3 |
| single answer, wrong | 1 |

On 26 of the 30 rows the reviewer gets either the answer or a two-to-four item list with
the answer on it. Picking the first candidate would score about six more and turn thirteen
honest shortlists into coin tosses presented as answers.

The same distinction applies across the board. `matched_sender_beneficiary` disagrees on
fourteen rows and sends eleven of them to a person. A column's `wrong` count mixes
"booked something incorrect" with "asked for help", and only the first is a defect.

## Three findings that belong to the client, not to us

These are not gaps in the matching. They are things in the client's own working file that
nothing here can derive, and each one is worth showing them:

1. **`ZZZ Operations` is booked on three rows and exists in no master list.** It occurs in
   exactly two places in the workbook — the `Staging Sheet` and the `DIU ` output. A value
   that reaches the journal without appearing in any reference list is precisely the thing
   nobody checks.
2. **38 entities sit on more than one sheet spelled differently** — `NI DRACONIS HOLDCO I
   SCSp` against `NI Draconis HoldCo I SCSp`, `NI V Kalvik TopCo Limited.` against the
   same name without its full stop. Whichever is written out, some sheet disagrees.
3. **A position string appears in the deal column** on one row.

## A note on reading this table

An earlier draft of it attributed the one `pulled_out_project_code` miss to the
counterparty guard in `matched_project_code`. The guard was not involved. The bank had
wrapped a line between the keyword and the name — `PROJECT, RANFJORD II.` — and the
pattern did not allow the comma. One character fixed it and the column went to 25/25.

That is the second plausible-sounding explanation in this work to survive until somebody
ran it; the first is recorded in [counterparty-matching.md](counterparty-matching.md),
where expanding the bank's abbreviations is the obvious fix and scores worse. Reasons for
missing points are worth checking against the output before they are written down.

## Reproducing

```bash
./run.sh
```

The per-row detail behind every line above comes from joining `data/rows.json` to the
`Staging Sheet` with `src.matcher.score.align`, which pairs on narrative, amount, bank
reference and account number — position alone lines up only 11 of the 100 rows.

See also [counterparty-matching.md](counterparty-matching.md) and
[deal-resolution.md](deal-resolution.md) for how the four hard columns work.
