"""Journal integrity, checked both ways: clean on the real DIU/CoA, caught when broken.

Run:  python -m pytest tests/ -q      (or: python tests/test_journal_integrity.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks import journal_integrity
from src.spine.build import load_workbook


def test_real_workbook_is_clean() -> None:
    """All 100 batches in the bundled 200-line DIU sheet are exactly two lines, balance
    to the cent, share one Transaction Reference per batch, and post only to CoA accounts
    marked Active. If this ever fails, a real data-quality issue was introduced upstream
    -- check the DIU/CoA sheets by hand before touching the check."""
    sheets = load_workbook()
    diu = sheets["DIU "]
    coa = sheets["CoA"]
    flags = journal_integrity.check(diu, coa)
    assert flags == [], f"expected a clean journal, got {len(flags)} flags: {flags[:3]}"


def _coa(account: str, status: str = "Active") -> dict:
    return {"Account": account, "Account Type": "Assets", "Account Active or Inactive": status}


def _line(batch: str, account: str, amount: str, is_debit: str, ref: str, trans_index: str = "1") -> dict:
    return {
        "Batch ID": batch,
        "JE Index": "1",
        "Trans Index": trans_index,
        "Account ": account,
        "is Debit": is_debit,
        "Amount (Local)": amount,
        "Transaction Reference": ref,
    }


def test_catches_an_unbalanced_batch() -> None:
    """100 debit against 90 credit leaves a residual of 10 -- should never post."""
    diu = [
        _line("B1", "10000", "100", "Yes", "REF1", "1"),
        _line("B1", "20000", "90", "No", "REF1", "2"),
    ]
    coa = [_coa("10000"), _coa("20000")]
    flags = journal_integrity.check(diu, coa)
    balance_flags = [f for f in flags if f.check == "batch_does_not_balance"]
    assert len(balance_flags) == 1
    assert balance_flags[0].severity == "error"
    assert balance_flags[0].expected == 0.0
    assert balance_flags[0].actual == 10.0
    assert balance_flags[0].source == {"batch_id": "B1"}


def test_catches_a_single_line_batch() -> None:
    """A batch with only one leg is missing its other half of the double entry."""
    diu = [_line("B2", "10000", "50", "Yes", "REF2", "1")]
    coa = [_coa("10000")]
    flags = journal_integrity.check(diu, coa)
    assert len(flags) == 1
    assert flags[0].check == "batch_single_line"
    assert flags[0].severity == "error"
    assert flags[0].expected == 2
    assert flags[0].actual == 1


def test_catches_a_reference_mismatch() -> None:
    """The two lines of a batch balance fine but disagree on Transaction Reference."""
    diu = [
        _line("B3", "10000", "75", "Yes", "REFA", "1"),
        _line("B3", "20000", "75", "No", "REFB", "2"),
    ]
    coa = [_coa("10000"), _coa("20000")]
    flags = journal_integrity.check(diu, coa)
    assert len(flags) == 1
    assert flags[0].check == "batch_reference_mismatch"
    assert flags[0].severity == "review"
    assert flags[0].actual == ["REFA", "REFB"]


def test_catches_a_posting_to_an_inactive_account() -> None:
    """A batch that balances and shares a reference can still post to a dead account."""
    diu = [
        _line("B4", "10000", "20", "Yes", "REF4", "1"),
        _line("B4", "99999", "20", "No", "REF4", "2"),
    ]
    coa = [_coa("10000"), _coa("99999", status="Inactive")]
    flags = journal_integrity.check(diu, coa)
    assert len(flags) == 1
    assert flags[0].check == "posted_to_inactive_account"
    assert flags[0].severity == "error"
    assert flags[0].source["account"] == "99999"
    assert flags[0].expected == "Active"
    assert flags[0].actual == "Inactive"


def test_a_clean_two_line_batch_raises_nothing() -> None:
    """Sanity: a well-formed batch (balances, one reference, both accounts active)
    should never be flagged by any of the four rules."""
    diu = [
        _line("B5", "10000", "42", "Yes", "REF5", "1"),
        _line("B5", "20000", "42", "No", "REF5", "2"),
    ]
    coa = [_coa("10000"), _coa("20000")]
    assert journal_integrity.check(diu, coa) == []


if __name__ == "__main__":
    test_real_workbook_is_clean()
    test_catches_an_unbalanced_batch()
    test_catches_a_single_line_batch()
    test_catches_a_reference_mismatch()
    test_catches_a_posting_to_an_inactive_account()
    test_a_clean_two_line_batch_raises_nothing()
    print("all journal_integrity checks pass")
