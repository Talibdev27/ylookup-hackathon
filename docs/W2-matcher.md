# W2 · The matcher

**Deliverable:** `data/rows.json` with all ten fields populated, every one carrying a
confidence, a status and an evidence span.

## Architecture: deterministic first

Normalise → generate candidates from the master lists by token overlap → accept on a
clear score margin → call an LLM **only** on the ambiguous residue, passing it the
narrative and the top 5 candidates.

Not LLM-first. You have 100 rows and about six hours: you need an iteration loop measured
in seconds and reproducible between runs, and W3's entire screen depends on being able to
show *why* a match was proposed. "The model said so" does not render.

## Order of attack

Two fields are fully deterministic. Do them in the first hour so there is always a
working pipeline to demo:

- `cash_leg_transtype` — currency + credit/debit sign. Implemented already.
- `matched_legal_entity` — Account Name against a 97-row master list.

Then the medium ones (`classification`, `counterparty_transtype`, `matched_project_code`),
then spend everything remaining on the counterparty pair.

## The numbers you are chasing

Human baseline on the 100 ground-truth rows:

| Field | Human filled |
|---|---|
| `pulled_out_sender_beneficiary` | 55 |
| `matched_sender_beneficiary` | **48** |
| `resolved_position` / `resolved_deal` | 30 |

The 52 blanks are the pitch. Resolve what you can, and mark the rest `unresolved` with
alternatives — never a silent blank.

## Two traps in the data

- **`matched_project_code` is not a lookup.** 30 of 100 rows carry the literal string
  `Flag for review - no project match`, and 26 carry `OH - Bank Fees`. Reproduce that
  vocabulary.
- **The docs and the data disagree on `classification`.** The Process sheet says the
  vocabulary is Investment / Vendor / Related Party / Investor / Internal / Review. The
  actual top values are `Other` (32), `Internal` (17), `Investment Transfer` (15).
  Trust the data.

Master list priority for counterparty matching: Related Party → Legal Entity → Investor
→ Vendor.
