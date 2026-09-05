# What an analyst would flag

Started as ideation; most of it is built now. Anything not marked *(built)* is still
open. See `docs/ARCHITECTURE.md` §9 for how a check plugs in, and
`docs/backend-integration.md` for the two API surfaces these come out through
(`/api/review` for dataset 1, `/api/gl-migration/flags` for dataset 2).

## 1 · Bank statement transactions (dataset 1)

| Flag | Why an analyst cares | Status |
|---|---|---|
| Balance does not foot | The statement's own running balance is wrong, or a transaction is missing from it | *(built)* `src/checks/footing.py`. Finds nothing on the sample data — the statements foot. |
| Documented rule vs. actual booking disagree | The client's own `Process` sheet is not what their file does | *(built, as a matcher stage)* `cash_leg_transtype` flags all 23 credit rows booked `Cash - Disbursed` against the sheet's own rule. Still not a standalone check — see `docs/where-the-points-go.md`. |
| No project code resolves | 30 of 100 rows are the client's own `Flag for review — no project match` | *(built)* Reproduced as-is by `matched_project_code`. |
| Duplicate transaction | Same bank reference, amount, date and account twice — double-booking or a bank error | *(built)* `src/checks/duplicates.py`. **0 flags on the sample** — several bank references do repeat (a wire and its fee, an internal transfer's two legs), but none also share the same signed amount, a real negative, not an unexercised rule. |
| Round-number transaction | A suspiciously exact amount often means an estimate rather than an invoiced figure | *(built)* `src/checks/round_numbers.py`. **24 flags** — threshold (≥3 trailing zeros) chosen from a real gap in the sample's own trailing-zero distribution, not picked to hit a target count. `severity="info"`, not an error. |
| Currency does not match the account's usual one | A transaction in an unexpected currency for an account is worth a second look | *(built)* `src/checks/currency_mismatch.py`. **0 flags** — every account in the sample is single-currency across every row, a real negative. |
| Posting to Suspense left unresolved | Suspense is a parking space for a human to investigate; an aged balance is a classic audit finding | Still open. Needs the row's `counterparty_transtype` value, which only exists after matching — the checking agent currently runs *before* matching (`pipeline.py`), so this needs a second, post-match check pass, not just a new module. |
| Related-party transaction with nothing explaining it | `classification = Related Party` with no narrative saying why is the weakest kind of proposal the matcher makes | *(partially built)* `classification` already sends this to `needs_review`. Not pulled out as its own count. |

## 2 · Reference data and journal entries (dataset 1)

| Flag | Why an analyst cares | Status |
|---|---|---|
| Same entity listed twice, spelled differently | A data-entry inconsistency in the client's own master list | *(built)* `src/checks/reference_quality.py`, run against the 97-row Legal Entity Master List. **0 exact-fold collisions.** 11 candidate near-duplicate pairs at a 0.9 token-overlap threshold, manually reviewed — none are real duplicates, each differs by one meaningful word (`NON`, `ELIMINATION`/`ELIMINATIONS`, `BLOCKED`) marking a genuinely distinct fund vehicle. Flagged `severity="review"` precisely because they're worth a glance, not because they're wrong. |
| Posting to an inactive account | A transaction booked to an account marked inactive in `CoA` is a control failure | *(built)* `src/checks/journal_integrity.py`. **0 flags** — all 558 CoA accounts are `Active`; there is no inactive account in this dataset to catch a posting to. |
| Batch does not balance | Double-entry's one hard rule | *(built)* `src/checks/journal_integrity.py`. **0 flags** — all 100 batches balance to the cent. |
| A batch has only one line | Every real batch here is two lines | *(built)* same module. **0 flags** — all 100 batches are exactly two lines. |
| The two lines of a pair don't share their join key | The pair is supposed to share `Transaction Reference` | *(built)* same module. **0 flags** — every pair matches. |
| Master-list entry never referenced by anything | Dead data, or a sign something upstream never got wired up | Still open — an anti-join across every reference list against every transaction, not built. |

Every "0 flags" above was verified by hand before being written down, not assumed —
`tests/test_journal_integrity.py`, `tests/test_reference_quality.py`,
`tests/test_duplicates.py`, `tests/test_round_numbers.py` and
`tests/test_currency_mismatch.py` each pin a synthetic broken case proving the rule
actually fires, alongside the real-data case proving today's data is genuinely clean.

## 3 · Investor-level GL → loader (dataset 2)

*(built)* `src/gl_migration/`, exposed at `GET /api/gl-migration/flags` — the first code
written against this dataset. Every count re-derived from the live workbooks, not
copied from the dataset's own README:

| Flag | Count | Matches README? |
|---|---|---|
| Legal entity in the upload template, missing from Entity Listing | **4** | Yes |
| Deal name in the upload template, missing from Deals List | **16** | Yes |
| Investor name in the mapping, missing from Investors List | **198** | Yes |
| Gaps the administrator itself flagged before upload (`Mapping Gaps` sheet) | **2** | README gives no number for this one |

**The new check, not in the README**: does the total tie between the source GL and the
upload template after the entity/deal/investor mapping is applied? Grouped by Legal
Entity (the only column with directly comparable, un-remapped values on both sides) and
verified by hand on one entity (1,522 rows each side, identical first-row amount,
both summing to 0.00) before trusting the aggregate — **every one of the 52 legal
entities common to both files ties to the cent.** The 27 source entities not yet in this
tranche are correctly excluded rather than forced to tie against nothing.

*(built)* Uploading a new tranche now works: `POST /gl-upload` accepts a GL workbook
and/or a loader workbook — either alone leaves the other on whatever it already was,
bundled sample or a previous upload, the same per-file independence dataset 1's workspace
uses — and `GET /api/gl-migration/flags` re-runs the five checks above against whichever
pair is current. See `src/gl_migration/workspace.py` and `tests/test_gl_workspace.py`.

Still open on dataset 2: `Movements Rec`, the administrator's own pre-upload
reconciliation sheet, isn't read yet — the items still open on it would be a sixth flag
type, not yet built.
