"""The review queue's ordering.

Ordering is the only logic in the UI worth pinning: everything else it does is wording,
which `test_labels.py` covers.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui.app import amount, flagged_discrepancy, queue_rank


def row(row_id: int, *, credit=None, debit=None, cash_leg: str = "auto") -> dict:
    return {
        "row_id": row_id,
        "raw": {"credit": credit, "debit": debit},
        "fields": {"cash_leg_transtype": {"status": cash_leg}},
    }


def entry(r: dict) -> dict:
    return {"row": r, "questions": [], "answered": {}}


def test_flagged_when_the_cash_leg_went_to_a_human() -> None:
    assert flagged_discrepancy(row(1, credit=100.0, cash_leg="needs_review"))
    assert flagged_discrepancy(row(2, credit=100.0, cash_leg="unresolved"))


def test_not_flagged_when_the_cash_leg_booked_itself() -> None:
    assert not flagged_discrepancy(row(3, debit=-100.0, cash_leg="auto"))


def test_a_row_without_a_cash_leg_is_not_flagged() -> None:
    """A stage that has not run yet must not read as a finding."""
    assert not flagged_discrepancy({"row_id": 4, "raw": {}, "fields": {}})


def test_amount_ignores_direction() -> None:
    assert amount(row(5, credit=301908.70)) == 301908.70
    assert amount(row(6, debit=-4232000.0)) == 4232000.0
    assert amount({"row_id": 7, "raw": {}}) == 0.0


def test_flagged_rows_come_before_larger_unflagged_ones() -> None:
    flagged = entry(row(8, credit=1000.0, cash_leg="needs_review"))
    bigger = entry(row(9, debit=-9_000_000.0, cash_leg="auto"))
    assert sorted([bigger, flagged], key=queue_rank) == [flagged, bigger]


def test_within_a_group_the_largest_payment_leads() -> None:
    small = entry(row(10, debit=-0.44))
    large = entry(row(11, debit=-4232000.0))
    middle = entry(row(12, debit=-301908.70))
    assert sorted([small, large, middle], key=queue_rank) == [large, middle, small]


def test_the_44_cent_charge_does_not_open_the_queue() -> None:
    """The regression this ordering exists for.

    In statement order the first card was a 44-cent bank charge asking four questions it
    could not answer, while the seven-figure rows carrying the Process-sheet
    contradiction sat below the fold.
    """
    charge = entry(row(13, debit=-0.44))
    cephalus = entry(row(14, credit=4232000.0, cash_leg="needs_review"))
    assert sorted([charge, cephalus], key=queue_rank)[0] is cephalus


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all ui checks pass")
