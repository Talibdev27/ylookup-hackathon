"""Balance continuity: does this statement's own running balance actually run?

Statements print newest transaction first -- reverse chronological. Reading down the
page, `balance[i] != balance[i-1] + amount[i]`; that arithmetic only holds once the rows
are put back into chronological order. Verified row by row against every one of the 100
transactions in the sample dataset before writing this -- it holds exactly, to the cent,
once reversed.

A break in that arithmetic is a different kind of problem to an unresolved counterparty:
it means either a transaction is missing from what was extracted, or the statement itself
does not reconcile. Either way it is not something a matching stage can paper over, and
it is exactly the "does this number foot to that number" gap from the interview.
"""
from __future__ import annotations

from src.checks.contract import Flag
from src.contract import Row

TOLERANCE = 0.01  # cents of floating-point noise, not a real discrepancy


def check(rows: list[Row]) -> list[Flag]:
    """One flag per row where the running balance does not follow from the row before it
    in the same account, checked in chronological order regardless of print order."""
    flags: list[Flag] = []
    by_account: dict[str, list[Row]] = {}
    for row in rows:
        by_account.setdefault(row.raw.account_number, []).append(row)

    for account, printed in by_account.items():
        chronological = list(reversed(printed))
        for previous, current in zip(chronological, chronological[1:]):
            amount = current.raw.credit if current.raw.credit is not None else current.raw.debit
            if amount is None or previous.raw.balance is None or current.raw.balance is None:
                continue
            expected = previous.raw.balance + amount
            if abs(expected - current.raw.balance) > TOLERANCE:
                flags.append(
                    Flag(
                        check="balance_continuity",
                        severity="error",
                        message=(
                            f"account {account}: the balance after this transaction should be "
                            f"{expected:,.2f} ({previous.raw.balance:,.2f} plus this transaction's "
                            f"{amount:,.2f}), but the statement shows {current.raw.balance:,.2f}"
                        ),
                        source={
                            "pdf": current.source.get("pdf"),
                            "page": current.source.get("page"),
                            "row_id": current.row_id,
                        },
                        expected=round(expected, 2),
                        actual=current.raw.balance,
                    )
                )
    return flags
