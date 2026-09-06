"""Currency mismatch: a row booked in a currency its own account does not use.

A bank account is opened in one currency and, in the ordinary case, every line on its
statement is denominated in that currency -- the account number itself usually even
encodes it, in the statement filename itself. A row whose
`raw.currency` differs from the currency the rest of that account's rows agree on is
either a mis-extracted field or a transaction that genuinely landed in the wrong place,
and either way it is worth a reviewer's attention before the amount is booked as if it
were the account's home currency.

Checked against the bundled dataset before writing this: all 7 accounts are single-currency
across every one of their rows (USD, DKK, EUR and GBP appear, but never mixed within one
account), so this finds nothing on the sample data -- correctly, since there is no minority
to flag.

Two guards keep this from manufacturing a signal that is not there:
  - an account needs an actual majority currency (the most common one strictly outnumbers
    every other currency on that account) before anything is called "dominant". A 50/50
    split between two currencies has no dominant one, so nothing is flagged -- picking a
    "correct" currency by coin flip is worse than staying silent.
  - an account with only one currency across all its rows has nothing to compare against,
    so it is skipped entirely rather than reported as "matches itself".
"""
from __future__ import annotations

from collections import Counter

from src.checks.contract import Flag
from src.contract import Row


def check(rows: list[Row]) -> list[Flag]:
    """One flag per row whose currency differs from its account's dominant currency,
    only for accounts where a dominant currency actually exists."""
    flags: list[Flag] = []
    by_account: dict[str, list[Row]] = {}
    for row in rows:
        by_account.setdefault(row.raw.account_number, []).append(row)

    for account, account_rows in by_account.items():
        counts = Counter(row.raw.currency for row in account_rows)
        if len(counts) < 2:
            continue  # only ever one currency here -- nothing to compare against

        [(dominant, top_count), *rest] = counts.most_common()
        if rest and rest[0][1] == top_count:
            continue  # tied for most common -- no real majority to call "dominant"

        for row in account_rows:
            if row.raw.currency == dominant:
                continue
            flags.append(
                Flag(
                    check="currency_mismatch",
                    severity="review",
                    message=(
                        f"account {account}: this row is in {row.raw.currency}, but "
                        f"{top_count} of {len(account_rows)} of this account's other rows "
                        f"are in {dominant}"
                    ),
                    source={
                        "pdf": row.source.get("pdf"),
                        "page": row.source.get("page"),
                        "row_id": row.row_id,
                    },
                    expected=dominant,
                    actual=row.raw.currency,
                )
            )
    return flags
