"""Duplicate transactions, checked both ways: clean on the real data, caught when broken.

Run:  python -m pytest tests/ -q      (or: python tests/test_duplicates.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks import duplicates
from src.contract import Raw, Row
from src.spine.build import STATEMENTS
from src.spine.pdf import parse_statements


def test_real_statements_have_no_duplicates() -> None:
    """None of the 100 sample transactions collide on reference, signed amount, value
    date and account together -- several bank references do repeat (a wire and its fee,
    or an internal transfer across two of the fund's own accounts), but never with the
    same amount too. If this ever starts flagging, check whether extraction started
    emitting the same statement line twice before assuming the check is wrong."""
    rows = parse_statements(STATEMENTS)
    flags = duplicates.check(rows)
    assert flags == [], f"expected no duplicates, got {len(flags)} flags: {flags[:3]}"


def _row(row_id: int, account: str, reference: str, amount: float, is_credit: bool, date: str) -> Row:
    raw = Raw(
        account_number=account,
        bank_reference=reference,
        value_date=date,
        credit=amount if is_credit else None,
        debit=None if is_credit else amount,
    )
    return Row(row_id=row_id, source={"pdf": "test.pdf", "page": 1}, raw=raw)


def test_catches_a_repeated_transaction() -> None:
    """Same reference, same signed amount, same date, same account, twice -- the second
    occurrence is the suspected duplicate and points back at the first."""
    rows = [
        _row(0, "ACC-1", "TT ABC123", 500.0, is_credit=True, date="2026-03-31"),
        _row(1, "ACC-1", "TT ABC123", 500.0, is_credit=True, date="2026-03-31"),
    ]
    flags = duplicates.check(rows)
    assert len(flags) == 1
    assert flags[0].check == "duplicate_transaction"
    assert len(flags[0].flag_id) == 24
    assert flags[0].severity == "review"
    assert flags[0].source == {"pdf": "test.pdf", "page": 1, "row_id": 1}
    assert flags[0].expected == 0
    assert flags[0].actual == 1
    assert "TT ABC123" in flags[0].message
    assert "500.00" in flags[0].message


def test_ignores_a_fee_sharing_the_same_reference() -> None:
    """A wire and its fee share a bank reference in the real data, but never the same
    amount -- this must not be mistaken for a duplicate."""
    rows = [
        _row(0, "ACC-1", "TT XYZ999", -6.87, is_credit=False, date="2026-03-31"),
        _row(1, "ACC-1", "TT XYZ999", -40000.0, is_credit=False, date="2026-03-31"),
    ]
    flags = duplicates.check(rows)
    assert flags == []


def test_ignores_an_internal_transfer_across_accounts() -> None:
    """An internal transfer shares a reference and a magnitude across two accounts, with
    opposite signs -- different signed amount, different account, so no flag."""
    rows = [
        _row(0, "ACC-1", "REF-1", -1000.0, is_credit=False, date="2026-03-31"),
        _row(1, "ACC-2", "REF-1", 1000.0, is_credit=True, date="2026-03-31"),
    ]
    flags = duplicates.check(rows)
    assert flags == []


if __name__ == "__main__":
    test_real_statements_have_no_duplicates()
    test_catches_a_repeated_transaction()
    test_ignores_a_fee_sharing_the_same_reference()
    test_ignores_an_internal_transfer_across_accounts()
    print("all duplicate checks pass")
