# What an analyst would flag

Ideation only — nothing below is implemented beyond what is explicitly marked *(built)*.
The point is to have a real list, grounded in the actual data, ready for whoever picks up
`src/checks/` next. See `docs/ROADMAP.md` for the checking-agent shape these would take.

## 1 · Bank statement transactions (dataset 1 — the one thing built end to end)

| Flag | Why an analyst cares | How it would be detected |
|---|---|---|
| Balance does not foot | The statement's own running balance is wrong, or a transaction is missing from it | *(built)* `src/checks/footing.py` — reverses each account into chronological order, checks `balance[i] == balance[i-1] + amount[i]`. Finds nothing on the sample data; the statements foot. |
| Documented rule vs. actual booking disagree | The client's own `Process` sheet is not what their file does — the thing the whole product argues about | *(built, as a matcher stage rather than a check)* `cash_leg_transtype` flags all 23 credit rows booked `Cash - Disbursed` against the sheet's own rule. Worth generalising into a standalone check rather than one stage's side effect — see `docs/where-the-points-go.md`. |
| No project code resolves | 30 of 100 rows are the client's own `Flag for review — no project match`, not a gap the matcher should paper over | Reproduced as-is by `matched_project_code`; an analyst reviewing the export would want these grouped and counted, not scattered through 100 rows. |
| Duplicate transaction | Same amount, same bank reference, same day, twice — double-booking or a bank error | Group rows by `(bank_reference, credit/debit amount, value_date, account_number)`; more than one row in a group is worth a human's eyes even if every field matched cleanly. |
| Round-number transaction | A suspiciously exact amount (`20,000.00`, `100,000.00`) often means an estimate or a manual entry rather than an invoiced figure | Amount modulo a threshold (e.g. divisible by 1,000 with no cents) — a standard audit heuristic, cheap to compute, worth a low-severity flag rather than a hard stop. |
| Posting to Suspense left unresolved | The Process sheet uses Suspense as a parking space for a human to investigate — an *aged* suspense balance is a classic audit finding | Any row where `counterparty_transtype` resolves to `Suspense (credit)` / `Suspense (debit)` and no reviewer decision exists in `data/decisions.json`. |
| Currency does not match the entity's usual currency | A handful of legal entities are held in more than one currency (`NI GMF II Coöperatief U.A.` vs `... - USD`); a transaction in an unexpected currency for that entity is worth a second look | Cross-reference `row.raw.currency` against which currency-suffixed variant of the entity actually matched. |
| Related-party transaction with nothing explaining it | `classification = Related Party` with no narrative text saying why is already the weakest kind of proposal the matcher makes | *(partially built)* `classification` already sends this case to `needs_review`; an analyst-facing summary would want these counted as their own category, since related-party dealings carry disclosure risk on their own. |

## 2 · The reference / master lists (the workbook's other 14 sheets)

| Flag | Why an analyst cares | How it would be detected |
|---|---|---|
| Same entity listed more than once, spelled differently | A data-entry inconsistency in the client's own master list, not something the matcher should have to work around forever | Fold every entry in a list (`counterparty.fold()` already does this) and look for two different raw spellings folding to the same value. |
| Posting to an inactive account | `CoA` carries `Account Active or Inactive` — a transaction booked to an account marked inactive is a control failure | Join a posted `Account`/`GL Account Code` against `CoA`'s active flag. |
| Master-list entry never referenced by anything | A legal entity, vendor or project code that exists in a list but never appears in a transaction, a deal, or a mapping — dead data, or a sign something upstream never got wired up | Anti-join: entries in a master list with zero matches across the transaction data. |
| Ambiguous currency-suffixed duplicates | Two master entries differing only by a trailing `- USD` / `- EUR` are the same legal entity in two currencies, not two entities — worth confirming rather than assuming | Already handled defensively in `counterparty.match()`'s scoring; worth a standing data-quality flag on the master list itself so it gets cleaned up rather than compensated for indefinitely. |

## 3 · Journal entries (`DIU`, the finished output)

| Flag | Why an analyst cares | How it would be detected |
|---|---|---|
| Batch does not balance | Double-entry's one hard rule: every batch's debits must equal its credits | Group `DIU` lines by `Batch ID`, sum signed `Amount (Local)`, expect zero. |
| A batch has only one line | Every real batch is two lines (per `docs/ROADMAP.md`'s Stage 6 notes) — one line means something failed to pair | Group by `Batch ID` and `JE Index`, flag any group of size 1. |
| The two lines of a pair do not share their join key | The pair is supposed to share `Transaction Reference` (`{date}_{amount}_{ccy}`) — a mismatch means the pairing itself is wrong, not just one field on it | Compare `Transaction Reference` across both lines of a `Batch ID`. |

## 4 · Investor-level GL → loader (dataset 2 — real data, nothing built against it yet)

Already counted in the dataset's own README, reproduced here because an analyst would
ask for exactly these as a starting checklist, not because they are new findings:

| Flag | Count | Source |
|---|---|---|
| Legal entity in the upload template, missing from the entity listing | 4 | `README.md` of dataset 02 |
| Deal name in the upload template, missing from the deals list | 16 | same |
| Investor name in the mapping, missing from the investors list | 198 | same |
| Gaps the administrator itself flagged before upload | populated `Mapping Gaps` sheet | same |
| Items still open on the administrator's own pre-upload reconciliation | `Movements Rec` sheet | same |

Beyond the counts already given: whether amounts still tie between the ~34,000-row source
GL and the ~18,930-row upload template after the entity/deal/investor mapping is applied
— a rollup by account that does not match before and after the transformation would be
the single most convincing check on this dataset, in the same spirit as `footing.py` for
statements.
