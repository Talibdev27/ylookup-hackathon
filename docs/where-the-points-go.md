# Where the remaining points go

Ten columns, scored against the human's own 100 answers by `./run.sh`. This is the
account of every point not scored, checked row by row against the current output rather
than reasoned about from the code.

| Field | Score | Reason for missing points |
|---|---|---|
| `matched_legal_entity` | 100/100 | — |
| `cash_leg_transtype` | 100/100 | — |
| `pulled_out_project_code` | 25/25 | — |
| `matched_sender_beneficiary` | 45/48 | Three rows name a group entity by an in-house alias — `NIP LIT` for `NIP P/S`, `NIP CINNABAR APS` for `NIP PLATFORM SOLUTIONS APS`. Neither alias appears anywhere in the workbook. Nothing is booked wrong: **its disagreement count is zero**, and all three are declined rather than guessed. |
| `matched_project_code` | 99/100 | One payment to an individual books to `OH - BOARD MEMBER FE`. That the payee is a board member is not in the bank text or any reference list. |
| `classification` | 98/100 | Two rows, both below. |
| `counterparty_transtype` | 98/100 | Both are inherited from those same two rows; the stage adds no error of its own. |
| `pulled_out_sender_beneficiary` | 53/55 | One row where the human wrote `Review` instead of a name. One trailing full stop, on which the human is self-contradictory — see below. |
| `resolved_deal` | 26/30 | Three want `ZZZ Operations EUR`/`GBP`, a bucket that exists in no reference list. One human answer is a position string in the deal column. |
| `resolved_position` | 26/30 | Three follow those `ZZZ Operations` deals. One is a shortlist that differs from the human's by a single deal. |

---

## The three kinds of remaining miss

Separating these matters, because only the first is a defect.

### Matcher limits — none left that we can see

Every remaining mismatch below is either evidence that does not exist or a contradiction
in the client's own file. There is no row where the bank text and the reference data
between them determine the answer and the matcher fails to reach it.

### Evidence that is not in the data (8 rows)

| Rows | Wanted | Why it cannot be derived |
|---|---|---|
| 19, 62, 67 | `NIP P/S`, `NIP PLATFORM SOLUTIONS APS` | `NIP LIT` and `NIP CINNABAR APS` appear **nowhere** in the workbook — not on any master list, not in the bank account report, not in the project codes. The link is in-house knowledge. This is what a client-maintained alias list is for; it is not something the statement or the reference data can supply. |
| 65 | `OH - BOARD MEMBER FE`, `Other`, `Accounts Payable` | The counterparty is a person's name. Nothing marks them as a board member. |
| 6 | `Review` on three columns | The narrative is a multi-leg loan distribution naming two entities and repaying principal in a third direction. The human gave up on it. Our answer, `NI ABF I DevCo ApS` on the vendor list, is a real name really in the text — it is a defensible reading, not a wrong one, and the human's `Review` is a judgement we have no signal for. |

### Contradictions in the client's own file (5 rows)

| Rows | The contradiction |
|---:|---|
| 33, 34, 86 | Booked to `ZZZ Operations EUR` / `GBP`. That string occurs in exactly two places in the workbook: the `Staging Sheet` and the `DIU ` loader output — both of which are the answers. It is an admin bucket that exists in their process and not in the reference data they gave us. **We decline these rather than invent the name.** |
| 1 | The deal column holds a *position* string, `Cephalus Biogas 001 Limited - EUR (Halstead (Funding Loan))`. Every other row puts a deal there. |
| 86 | Structurally identical to rows 94 and 97 — same account, same `SHORT TERM LOAN: FROM NI V SCSP TO NI V CN SCSP`, differing only in which project is named. Those two get real deals; this one gets the admin bucket, with nothing in the text to separate them. |
| 96 | The human keeps the bank's trailing full stop here (`NI V FENWICK HOLDCO LTD.`) and drops it on row 50 (`NI GMF II COOPERATIEF U.A`), from statements written the same way. Either rule scores one and loses the other. |
| 97 | Our Fenwick shortlist and the human's differ by one deal out of five. |

---

## What the scoreboard cannot see

A column's `wrong` count mixes "booked something incorrect" with "asked a person", and
only the first is a defect. Across all ten columns there are now **7 disagreements**, and
`matched_sender_beneficiary` — the hardest column on the sheet — has **none**: every row
it does not reproduce is one it declines.

`resolved_position` reads 26/30, and the four it misses are all downstream of a deal that
does not exist in the reference data.

Three rows are answered with a shortlist rather than a single value, under the client's own
heading `Review - multiple positions:`. That is what their working file says where the same
thing happened to them.

---

## A note on reading this table

An earlier draft attributed the one `pulled_out_project_code` miss to the counterparty
guard in `matched_project_code`. The guard was not involved. The bank had wrapped a line
between the keyword and the name — `PROJECT, RANFJORD II.` — and the pattern did not allow
the comma. One character fixed it and the column went to 25/25.

That is one of several plausible-sounding explanations in this work that survived until
somebody ran it. `counterparty-matching.md` records two more: expanding the bank's
abbreviations globally is the obvious fix and scores worse, and applying the other-party
rule to every row costs nine matches. Reasons for missing points are worth checking
against the output before they are written down.

## Reproducing

```bash
./run.sh
```

The per-row detail behind every line above comes from joining `data/rows.json` to the
`Staging Sheet` with `src.matcher.score.align`, which pairs on narrative, amount, bank
reference and account number — position alone lines up only 11 of the 100 rows.

`score.py` is the only module that reads the `Staging Sheet`, and nothing in `src/`
imports it. No stage can see the answers.

See also [counterparty-matching.md](counterparty-matching.md) and
[deal-resolution.md](deal-resolution.md) for how the hard columns work.
