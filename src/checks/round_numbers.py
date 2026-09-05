"""Suspiciously round amounts: the classic "this looks like an estimate" audit heuristic.

A real invoice or a calculated fee almost never lands on an exact multiple of a thousand;
an estimate, a placeholder, or a manually keyed figure often does. This is a soft signal
for a reviewer to glance at, not proof of anything wrong -- plenty of round transfers are
entirely genuine (funding calls and capital drawdowns are quoted in round numbers on
purpose). That is why it is `info`, not `review` or `error`.

Threshold picked from the real data, not guessed: of the 100 sample transactions, 33 have
a whole-number amount (no cents at all). Counting trailing zeros on those 33 shows a gap
in the distribution -- 7 have none, 1 has exactly one, 1 has exactly two, and then it jumps
to 6 with three, 10 with four, 5 with five, 2 with six and 1 with seven. Three trailing
zeros is where that gap sits: below it, amounts look like arbitrary whole numbers (e.g. a
single-digit-cents narrative rounds to a whole dollar by coincidence); at or above it, 24
of the 33 whole-number rows cluster together, round to the nearest thousand or more. So
the rule is: a non-zero, whole-number amount with three or more trailing zeros, i.e.
divisible by 1,000.
"""
from __future__ import annotations

from src.checks.contract import Flag
from src.contract import Row

TRAILING_ZERO_THRESHOLD = 1000  # amounts divisible by this look like an estimate, not an invoice


def check(rows: list[Row]) -> list[Flag]:
    """One flag per row whose credit or debit amount is a non-zero whole number
    divisible by 1,000 -- the round-number signature an estimate tends to leave."""
    flags: list[Flag] = []

    for row in rows:
        amount = row.raw.credit if row.raw.credit is not None else row.raw.debit
        if amount is None or amount == 0:
            continue
        if amount != int(amount):
            continue
        if int(amount) % TRAILING_ZERO_THRESHOLD != 0:
            continue

        flags.append(
            Flag(
                check="round_number",
                severity="info",
                message=(
                    f"account {row.raw.account_number}: this transaction's amount, "
                    f"{amount:,.2f}, is a round multiple of {TRAILING_ZERO_THRESHOLD:,} -- "
                    f"worth a glance in case it is an estimate rather than an invoiced figure"
                ),
                source={
                    "pdf": row.source.get("pdf"),
                    "page": row.source.get("page"),
                    "row_id": row.row_id,
                },
                expected=None,
                actual=amount,
            )
        )
    return flags
