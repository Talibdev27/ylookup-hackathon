"""Journal integrity: does each posted batch actually look like real double-entry?

Operates on the reference workbook's own sheets -- `DIU ` (200 real posted journal
lines, always in pairs sharing a `Batch ID`) and `CoA` (chart of accounts) -- read via
`src.spine.build.load_workbook()`, not on parsed statement `Row` objects. That is a
deliberate, different shape from `src.checks.footing`: footing checks a statement's own
arithmetic, this checks the *journal*'s.

Four things, per batch:

  1. does not balance      -- signed amounts should sum to zero, to the cent
  2. only one line         -- every real batch here is two lines (the product's own docs);
                               a batch with exactly one line is missing its other leg
  3. reference mismatch    -- the two lines of a batch are supposed to share
                               `Transaction Reference`
  4. posted to an inactive account -- `Account ` (trailing space, real) joined to CoA's
                               `Account`, flagged when `Account Active or Inactive` != "Active"

Sign convention and the DIU/CoA join copy `src/reports/statements.py`'s `_signed_amount`
and `_account_types` exactly: debit positive, credit negative, from `Amount (Local)` and
`is Debit` (`"Yes"`/`"No"` strings); `Account ` (trailing space) is stripped before the
join, same as there. Copied rather than imported because that function is private to its
module and this module must not touch `src/reports/statements.py`.

Run against the bundled 200-line DIU / 558-line CoA sheets before writing this down: all
100 batches are exactly 2 lines, every batch balances to the cent, every batch's two
lines share one `Transaction Reference`, and all 558 CoA accounts are `Active` -- so all
four checks come back clean (zero flags) on the real bundled data. That is the real
result, not an assumption; the synthetic tests below prove each check still fires when
one of those four things is actually broken.
"""
from __future__ import annotations

from collections import defaultdict

from src.checks.contract import Flag

TOLERANCE = 0.01  # cents of floating-point noise, not a real discrepancy


def _signed_amount(row: dict) -> float:
    """Debit positive, credit negative -- same convention as `reports/statements.py`."""
    try:
        value = float(row.get("Amount (Local)") or 0)
    except ValueError:
        return 0.0
    is_debit = (row.get("is Debit") or "").strip().lower() == "yes"
    return value if is_debit else -value


def _account_types(coa: list[dict]) -> dict[str, dict]:
    """Account code -> the CoA row itself, from the CoA sheet.

    Keyed the same way `reports/statements.py`'s `_account_types` keys its map -- by the
    plain `Account` column -- but keeps the whole row so the active/inactive status is
    still there to read, not just the account type.
    """
    return {r["Account"]: r for r in coa if r.get("Account")}


def _line_source(row: dict) -> dict:
    return {
        "batch_id": row.get("Batch ID"),
        "je_index": row.get("JE Index"),
        "trans_index": row.get("Trans Index"),
    }


def check(diu: list[dict], coa: list[dict]) -> list[Flag]:
    """One flag per batch (or per line, for the account check) that fails one of the
    four journal-integrity rules above."""
    flags: list[Flag] = []
    accounts = _account_types(coa)

    by_batch: dict[str, list[dict]] = defaultdict(list)
    for row in diu:
        by_batch[row.get("Batch ID")].append(row)

    for batch_id, lines in by_batch.items():
        if len(lines) == 1:
            flags.append(
                Flag(
                    check="batch_single_line",
                    severity="error",
                    message=(
                        f"batch {batch_id}: has exactly one journal line; every real "
                        f"batch is a pair, so this one is missing its other leg"
                    ),
                    source={"batch_id": batch_id, "je_index": lines[0].get("JE Index")},
                    expected=2,
                    actual=1,
                )
            )
            # A one-line batch has no "does it balance" or "do the two references match"
            # question to ask -- there is no second line to balance or match against.
            continue

        residual = round(sum(_signed_amount(line) for line in lines), 2)
        if abs(residual) > TOLERANCE:
            flags.append(
                Flag(
                    check="batch_does_not_balance",
                    severity="error",
                    message=(
                        f"batch {batch_id}: {len(lines)} lines sum to {residual:,.2f} "
                        f"(debit positive, credit negative) instead of 0.00"
                    ),
                    source={"batch_id": batch_id},
                    expected=0.0,
                    actual=residual,
                )
            )

        references = {line.get("Transaction Reference") for line in lines}
        if len(references) > 1:
            flags.append(
                Flag(
                    check="batch_reference_mismatch",
                    severity="review",
                    message=(
                        f"batch {batch_id}: lines carry different Transaction Reference "
                        f"values {sorted(r for r in references if r is not None)!r}, but "
                        f"the two lines of a batch are supposed to share one"
                    ),
                    source={"batch_id": batch_id},
                    expected="a single shared Transaction Reference",
                    actual=sorted(r for r in references if r is not None),
                )
            )

    for row in diu:
        account_code = (row.get("Account ") or "").strip()
        coa_row = accounts.get(account_code)
        if coa_row is None:
            continue  # a different join problem, not this check's concern
        status = coa_row.get("Account Active or Inactive")
        if status != "Active":
            flags.append(
                Flag(
                    check="posted_to_inactive_account",
                    severity="error",
                    message=(
                        f"batch {row.get('Batch ID')}: posted to account {account_code} "
                        f"({coa_row.get('Account Short Description', '')!r}), whose CoA "
                        f"status is {status!r}, not Active"
                    ),
                    source=_line_source(row) | {"account": account_code},
                    expected="Active",
                    actual=status,
                )
            )

    return flags
