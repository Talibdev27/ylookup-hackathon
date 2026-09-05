"""Currency mismatch, checked both ways: clean on the real data, caught when broken.

Run:  python -m pytest tests/ -q      (or: python tests/test_currency_mismatch.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks import currency_mismatch
from src.contract import Raw, Row
from src.spine.build import STATEMENTS
from src.spine.pdf import parse_statements


def test_real_statements_are_single_currency_per_account() -> None:
    """All 7 accounts in the sample data are single-currency across every one of their
    rows -- verified directly against the parsed rows before writing this test. If this
    ever starts flagging, check whether extraction started misreading the currency
    column before assuming the check is wrong."""
    rows = parse_statements(STATEMENTS)
    flags = currency_mismatch.check(rows)
    assert flags == [], f"expected no currency mismatches, got {len(flags)} flags: {flags[:3]}"


def _row(row_id: int, account: str, currency: str) -> Row:
    raw = Raw(account_number=account, currency=currency, credit=100.0)
    return Row(row_id=row_id, source={"pdf": "test.pdf", "page": 1}, raw=raw)


def test_catches_a_minority_currency() -> None:
    """Three rows in USD and one in EUR on the same account -- USD is the clear
    majority, so the EUR row is the mismatch."""
    rows = [
        _row(0, "ACC-1", "USD"),
        _row(1, "ACC-1", "USD"),
        _row(2, "ACC-1", "USD"),
        _row(3, "ACC-1", "EUR"),
    ]
    flags = currency_mismatch.check(rows)
    assert len(flags) == 1
    assert flags[0].check == "currency_mismatch"
    assert len(flags[0].flag_id) == 24
    assert flags[0].severity == "review"
    assert flags[0].source == {"pdf": "test.pdf", "page": 1, "row_id": 3}
    assert flags[0].expected == "USD"
    assert flags[0].actual == "EUR"


def test_ignores_a_single_currency_account() -> None:
    """An account that only ever appears in one currency has nothing to compare
    against."""
    rows = [_row(0, "ACC-1", "GBP"), _row(1, "ACC-1", "GBP")]
    flags = currency_mismatch.check(rows)
    assert flags == []


def test_ignores_a_tied_split_with_no_dominant_currency() -> None:
    """A 50/50 split between two currencies has no real majority -- picking one as
    "dominant" would be a coin flip, so nothing is flagged."""
    rows = [_row(0, "ACC-1", "USD"), _row(1, "ACC-1", "EUR")]
    flags = currency_mismatch.check(rows)
    assert flags == []


if __name__ == "__main__":
    test_real_statements_are_single_currency_per_account()
    test_catches_a_minority_currency()
    test_ignores_a_single_currency_account()
    test_ignores_a_tied_split_with_no_dominant_currency()
    print("all currency-mismatch checks pass")
