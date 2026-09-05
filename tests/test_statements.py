"""Balance sheet / income statement rollup, against the real DIU and CoA sheets --
not fakes, because whether the account-code join and the debit/credit sign convention
actually hold is exactly the thing that would be wrong to assume.

Run:  python -m pytest tests/ -q      (or: python tests/test_statements.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reports import statements
from src.spine.build import load_workbook


def _sheets():
    sheets = load_workbook()
    diu = sheets[[name for name in sheets if name.strip() == "DIU"][0]]
    return diu, sheets["CoA"]


def test_the_expanded_accounting_equation_ties_on_real_data() -> None:
    """Assets = Liabilities + Capital + Revenues - Expenses. Verified by hand before
    writing statements.py -- the residual is exactly zero, which is what real
    double-entry postings look like, not something a rollup should have to force."""
    diu, coa = _sheets()
    totals = statements._totals(diu, coa, legal_entity=None)
    assert statements.ties(totals)


def test_legal_entities_lists_the_four_real_funds() -> None:
    diu, _ = _sheets()
    assert statements.legal_entities(diu) == [
        "Nordvik Infrastructure Advanced Bioenergy Fund I SCSp",
        "Nordvik Infrastructure Advanced Bioenergy Fund II SCSp",
        "Nordvik Infrastructure Growth Markets Fund II SCSp",
        "Nordvik Infrastructure V SCSp",
    ]


def test_balance_sheet_shape_and_period_caveat() -> None:
    diu, coa = _sheets()
    result = statements.balance_sheet(diu, coa)
    assert set(result) == {"legal_entity", "period", "assets", "liabilities", "capital", "ties"}
    assert "no opening balance" in result["period"]
    assert result["ties"] is True


def test_income_statement_shape() -> None:
    diu, coa = _sheets()
    result = statements.income_statement(diu, coa)
    assert set(result) == {"legal_entity", "period", "revenues", "expenses", "net_income"}
    assert result["net_income"] == round(result["revenues"] - result["expenses"], 2)


def test_per_entity_rollup_is_a_real_subset_not_the_whole_book() -> None:
    diu, coa = _sheets()
    whole = statements.balance_sheet(diu, coa)
    one_fund = statements.balance_sheet(
        diu, coa, legal_entity="Nordvik Infrastructure V SCSp"
    )
    assert one_fund["legal_entity"] == "Nordvik Infrastructure V SCSp"
    assert one_fund["assets"] != whole["assets"], "a single fund should not equal the combined book"


def test_unknown_legal_entity_returns_zeros_not_the_whole_book() -> None:
    diu, coa = _sheets()
    result = statements.balance_sheet(diu, coa, legal_entity="Not A Real Fund")
    assert result["assets"] == result["liabilities"] == result["capital"] == 0.0


if __name__ == "__main__":
    test_the_expanded_accounting_equation_ties_on_real_data()
    test_legal_entities_lists_the_four_real_funds()
    test_balance_sheet_shape_and_period_caveat()
    test_income_statement_shape()
    test_per_entity_rollup_is_a_real_subset_not_the_whole_book()
    test_unknown_legal_entity_returns_zeros_not_the_whole_book()
    print("all statement checks pass")
