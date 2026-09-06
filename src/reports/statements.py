"""A balance sheet and an income statement, rolled up from the real `DIU` journal lines.

Not derived from the matcher's own output -- the matcher does not produce journal
entries; turning its answers into one was cut from scope. This reads the `DIU` sheet
already present in the reference workbook instead: 200 real
posted lines, joined to the `CoA` sheet's real chart-of-accounts categories on `Account`.
Every account code in `DIU` matched a `CoA` entry exactly when this was checked against
the bundled sample -- no fuzzy join, no guessing.

The one caveat that matters, and that both functions below say in their own return
value rather than let a caller assume otherwise: `DIU` is one week's activity, not a
ledger since inception. This is a movements statement for the period the uploaded
statements cover, not a true point-in-time balance sheet -- there is no opening balance
anywhere in this data.

`ties()` checks the one thing that has to be true regardless of the period covered: the
expanded accounting equation, Assets = Liabilities + Capital + Revenues - Expenses.
Verified by hand against the bundled sample before writing this -- the residual is
exactly zero, which is what "the postings are real double-entry bookkeeping" looks like
numerically.
"""
from __future__ import annotations

# The five categories the CoA sheet actually uses -- not the six the Process sheet
# describes for classification (a different vocabulary for a different question) --
# and which normal-balance direction each is positive in. Debit
# increases Assets and Expenses; credit increases everything else. The opposite of debit
# is not "negative", it is the account's own normal balance.
DEBIT_NORMAL = {"Assets", "Expenses"}
ALL_TYPES = ("Assets", "Liabilities", "Capital", "Revenues", "Expenses")
BALANCE_SHEET_TYPES = ("Assets", "Liabilities", "Capital")
INCOME_STATEMENT_TYPES = ("Revenues", "Expenses")

PERIOD_CAVEAT = (
    "Movements in the uploaded statements only. There is no opening balance in this "
    "data, so this is a period movements statement, not a point-in-time balance sheet."
)


def _signed_amount(row: dict) -> float:
    try:
        value = float(row.get("Amount (Local)") or 0)
    except ValueError:
        return 0.0
    is_debit = (row.get("is Debit") or "").strip().lower() == "yes"
    return value if is_debit else -value


def _account_types(coa: list[dict]) -> dict[str, str]:
    """Account code -> Account Type, from the CoA sheet."""
    return {r["Account"]: r["Account Type"] for r in coa if r.get("Account")}


def legal_entities(diu: list[dict]) -> list[str]:
    """Every fund with activity in this DIU -- the natural "company" list for a
    per-entity rollup, since DIU mixes more than one fund's postings together."""
    return sorted({row["Legal Entity"] for row in diu if row.get("Legal Entity")})


def _totals(diu: list[dict], coa: list[dict], legal_entity: str | None) -> dict[str, float]:
    account_types = _account_types(coa)
    totals: dict[str, float] = {t: 0.0 for t in ALL_TYPES}
    for row in diu:
        if legal_entity and row.get("Legal Entity") != legal_entity:
            continue
        account = (row.get("Account ") or "").strip()  # trailing space is real, see README
        account_type = account_types.get(account)
        if account_type not in totals:
            continue
        signed = _signed_amount(row)
        totals[account_type] += signed if account_type in DEBIT_NORMAL else -signed
    return {k: round(v, 2) for k, v in totals.items()}


def ties(totals: dict[str, float]) -> bool:
    """Assets = Liabilities + Capital + Revenues - Expenses, to the cent."""
    residual = (
        totals["Assets"] - totals["Liabilities"] - totals["Capital"]
        - totals["Revenues"] + totals["Expenses"]
    )
    return abs(residual) < 0.01


def balance_sheet(diu: list[dict], coa: list[dict], legal_entity: str | None = None) -> dict:
    totals = _totals(diu, coa, legal_entity)
    return {
        "legal_entity": legal_entity,
        "period": PERIOD_CAVEAT,
        "assets": totals["Assets"],
        "liabilities": totals["Liabilities"],
        "capital": totals["Capital"],
        "ties": ties(totals),
    }


def income_statement(diu: list[dict], coa: list[dict], legal_entity: str | None = None) -> dict:
    totals = _totals(diu, coa, legal_entity)
    return {
        "legal_entity": legal_entity,
        "period": PERIOD_CAVEAT,
        "revenues": totals["Revenues"],
        "expenses": totals["Expenses"],
        "net_income": round(totals["Revenues"] - totals["Expenses"], 2),
    }
