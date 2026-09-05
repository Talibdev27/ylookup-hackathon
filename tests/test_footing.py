"""Balance continuity, checked both ways: clean on the real data, caught when broken.

Run:  python -m pytest tests/ -q      (or: python tests/test_footing.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks import footing
from src.contract import Raw, Row
from src.spine.build import STATEMENTS
from src.spine.pdf import parse_statements


def test_real_statements_reconcile() -> None:
    """Every one of the 100 sample transactions foots against its own statement once put
    back into chronological order. If this ever fails, either a row went missing from
    extraction or the assumption print order is reverse-chronological stopped holding --
    check the raw PDF before touching the check."""
    rows = parse_statements(STATEMENTS)
    flags = footing.check(rows)
    assert flags == [], f"expected a clean reconciliation, got {len(flags)} flags: {flags[:3]}"


def _row(account: str, row_id: int, amount: float, balance: float, is_credit: bool) -> Row:
    raw = Raw(
        account_number=account,
        credit=amount if is_credit else None,
        debit=None if is_credit else amount,
        balance=balance,
    )
    return Row(row_id=row_id, source={"pdf": "test.pdf", "page": 1}, raw=raw)


def test_catches_a_broken_balance() -> None:
    """Printed newest-first, like a real statement: row_id 1 is the most recent. 100
    opening plus a 50 credit should read 150; the statement wrongly shows 200."""
    rows = [
        _row("ACC-1", row_id=1, amount=50.0, balance=200.0, is_credit=True),  # newest, wrong
        _row("ACC-1", row_id=0, amount=-10.0, balance=100.0, is_credit=False),  # oldest
    ]
    flags = footing.check(rows)
    assert len(flags) == 1
    assert flags[0].check == "balance_continuity"
    assert len(flags[0].flag_id) == 24
    assert flags[0].severity == "error"
    assert flags[0].source == {"pdf": "test.pdf", "page": 1, "row_id": 1}
    assert flags[0].expected == 150.0
    assert flags[0].actual == 200.0
    assert "should be 150.00" in flags[0].message


def test_ignores_other_accounts() -> None:
    """One account's break should never flag rows belonging to a different account."""
    rows = [
        _row("ACC-1", row_id=1, amount=10.0, balance=999.0, is_credit=True),  # newest, broken
        _row("ACC-1", row_id=0, amount=0.0, balance=5.0, is_credit=True),  # oldest
        _row("ACC-2", row_id=3, amount=10.0, balance=20.0, is_credit=True),  # newest, clean
        _row("ACC-2", row_id=2, amount=5.0, balance=10.0, is_credit=True),  # oldest, clean
    ]
    flags = footing.check(rows)
    assert len(flags) == 1
    assert flags[0].source["row_id"] == 1


if __name__ == "__main__":
    test_real_statements_reconcile()
    test_catches_a_broken_balance()
    test_ignores_other_accounts()
    print("all footing checks pass")
