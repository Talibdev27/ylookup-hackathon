"""Round-number amounts, checked both ways: known count on the real data, caught when
introduced synthetically.

Run:  python -m pytest tests/ -q      (or: python tests/test_round_numbers.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks import round_numbers
from src.contract import Raw, Row
from src.spine.build import STATEMENTS
from src.spine.pdf import parse_statements


def test_real_statements_flag_the_known_round_amounts() -> None:
    """24 of the 100 sample transactions have a whole-number amount divisible by 1,000 --
    verified directly against the parsed rows before writing this test. If this count
    ever changes, check whether extraction changed before assuming the check is wrong."""
    rows = parse_statements(STATEMENTS)
    flags = round_numbers.check(rows)
    assert len(flags) == 24, f"expected 24 round-number flags, got {len(flags)}: {flags[:3]}"
    assert all(f.check == "round_number" for f in flags)
    assert all(f.severity == "info" for f in flags)


def _row(row_id: int, amount: float, is_credit: bool) -> Row:
    raw = Raw(
        account_number="ACC-1",
        credit=amount if is_credit else None,
        debit=None if is_credit else amount,
    )
    return Row(row_id=row_id, source={"pdf": "test.pdf", "page": 1}, raw=raw)


def test_catches_a_round_amount() -> None:
    """A clean multiple of 1,000 is exactly the estimate-shaped figure this check looks
    for."""
    rows = [_row(0, 5000.0, is_credit=True)]
    flags = round_numbers.check(rows)
    assert len(flags) == 1
    assert flags[0].check == "round_number"
    assert len(flags[0].flag_id) == 24
    assert flags[0].severity == "info"
    assert flags[0].source == {"pdf": "test.pdf", "page": 1, "row_id": 0}
    assert flags[0].actual == 5000.0
    assert "5,000.00" in flags[0].message


def test_ignores_amounts_below_the_threshold() -> None:
    """A whole number under three trailing zeros, an amount with cents, and a zero
    amount all have no round-number signature worth raising."""
    rows = [
        _row(0, 500.0, is_credit=True),  # only two trailing zeros
        _row(1, 12345.0, is_credit=True),  # whole number, no trailing zeros
        _row(2, 3000.50, is_credit=True),  # not a whole number
        _row(3, 0.0, is_credit=True),  # zero is not "round" in the way that matters here
    ]
    flags = round_numbers.check(rows)
    assert flags == []


if __name__ == "__main__":
    test_real_statements_flag_the_known_round_amounts()
    test_catches_a_round_amount()
    test_ignores_amounts_below_the_threshold()
    print("all round-number checks pass")
