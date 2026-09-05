"""Stage 6: staging rows -> DIU journal entries.  W4 owns this.

Verified against the real DIU sheet: 29 columns, 200 lines, two per Batch ID.

The pair for one batch:
  - shares `Batch ID` and `JE Index`
  - splits on `is Debit` ("Yes" / "No"), with `Trans Index` 1 and 2
  - carries the same `Amount (Local)`
  - shares `Transaction Reference`, a composite key: "{value_date_serial}_{amount}_{ccy}"
    e.g. "46112_0.44_EUR" -- this is also the join key back to the staging row

Worked example from the real file (batch 1, a EUR bank charge of 0.44):
  line 1  Transaction Type "Cash - Disbursed - EUR"   is Debit "No"   Allocation "Non Dominant"
  line 2  Transaction Type "Expense - Bank Charges"   is Debit "Yes"  Allocation "No Allocation"
"""
from __future__ import annotations

DIU_COLUMNS = [
    "Legal Entity", "Transaction Type", "Legal Entity Domain", "Deal Name", "Position",
    "Batch ID", "JE Index", "Trans Index", "GL Date", "Effective Date",
    "Transaction currency", "Allocation Rule", "Trans Type Sub Category", "is Debit",
    "Amount (Local)", "Amount (LE)", "Quantity", "Transaction Comments", "Related Party",
    "CostName", "ReasonName", "Transaction GL Reference", "Batch Comments", "Bank Account",
    "Comments 2", "Transaction Reference", "Vendor", "Account ", "Project Code",
]


def transaction_reference(value_date_serial: int, amount: float, currency: str) -> str:
    """The composite key joining a journal line back to its staging row."""
    return f"{value_date_serial}_{amount}_{currency}"


def build_batch(row: dict) -> list[dict]:
    """Two journal lines from one reviewed staging row."""
    raise NotImplementedError("W4")
