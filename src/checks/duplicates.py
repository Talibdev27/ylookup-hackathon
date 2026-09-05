"""Duplicate transactions: the same wire counted twice.

A bank reference is the bank's own idea of "one transaction." If it, the signed amount,
the value date and the account it landed on all match another row, that is not two
payments that happen to look alike -- it is one payment that got extracted, or booked,
twice. Left alone it would double the cash movement in the journal.

Checked against the 100 sample transactions before writing this: several bank references
repeat (a wire and its fee share a reference, and an internal transfer shares one across
the two accounts it moves between), but none of those pairs also share the signed amount
-- the fee is a few cents against a six- or seven-figure principal, and a cross-account
transfer is the same amount with opposite sign on two different accounts. So requiring all
four fields together, not the reference alone, is what keeps a fee/principal pair or an
internal transfer from being mistaken for a duplicate. On the bundled dataset this finds
nothing, which is the correct answer for a dataset that reconciles.
"""
from __future__ import annotations

from src.checks.contract import Flag
from src.contract import Row


def check(rows: list[Row]) -> list[Flag]:
    """One flag per row after the first in any group sharing bank reference, signed
    amount, value date and account number -- the group's first occurrence is the
    transaction; everything after it in that group is the suspected duplicate."""
    flags: list[Flag] = []
    seen: dict[tuple, Row] = {}

    for row in rows:
        amount = row.raw.credit if row.raw.credit is not None else row.raw.debit
        key = (row.raw.bank_reference, amount, row.raw.value_date, row.raw.account_number)
        first = seen.get(key)
        if first is None:
            seen[key] = row
            continue

        flags.append(
            Flag(
                check="duplicate_transaction",
                severity="review",
                message=(
                    f"account {row.raw.account_number}: bank reference "
                    f"{row.raw.bank_reference!r} for {amount:,.2f} on {row.raw.value_date} "
                    f"already appears on row {first.row_id} -- this looks like the same "
                    f"transaction counted twice"
                ),
                source={
                    "pdf": row.source.get("pdf"),
                    "page": row.source.get("page"),
                    "row_id": row.row_id,
                },
                expected=first.row_id,
                actual=row.row_id,
            )
        )
    return flags
