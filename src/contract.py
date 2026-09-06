"""The row contract. Shared by every workstream. See CONTRACT.md."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal, Optional

Status = Literal["auto", "needs_review", "unresolved"]

# The eight fields the matcher fills, in Process-sheet order.
FIELD_KEYS = [
    "matched_legal_entity",
    "pulled_out_project_code",
    "matched_project_code",
    "pulled_out_sender_beneficiary",
    "matched_sender_beneficiary",
    "classification",
    "cash_leg_transtype",
    "counterparty_transtype",
    "resolved_deal",
    "resolved_position",
]

# Ground-truth column in the Staging Sheet for each field key, so score.py and the
# spine loader agree on what maps to what.
STAGING_COLUMN = {
    "matched_legal_entity": "Matched Legal Entity",
    "pulled_out_project_code": "Pulled Out Project Code",
    "matched_project_code": "Matched Project Code",
    "pulled_out_sender_beneficiary": "Pulled Out Sender/Beneficiary",
    "matched_sender_beneficiary": "Matched Sender/Beneficiary",
    "classification": "Classification",
    "cash_leg_transtype": "Cash Leg Transtype",
    "counterparty_transtype": "Counterparty Transtype",
    "resolved_deal": "Resolved Deal",
    "resolved_position": "Resolved Position",
}


@dataclass
class Evidence:
    """Where a value came from. span indexes into raw.narrative_raw, never the normalised form."""

    span: Optional[tuple[int, int]] = None
    text: str = ""
    source_list: str = ""


@dataclass
class Alternative:
    value: str
    confidence: float


@dataclass
class Field:
    value: Optional[str] = None
    confidence: float = 0.0
    status: Status = "unresolved"
    evidence: Evidence = field(default_factory=Evidence)
    alternatives: list[Alternative] = field(default_factory=list)


@dataclass
class Raw:
    account_name: str = ""
    account_number: str = ""
    currency: str = ""
    bank_reference: str = ""
    narrative_raw: str = ""
    narrative_normalised: str = ""
    value_date: Optional[str] = None
    post_date: Optional[str] = None
    credit: Optional[float] = None
    debit: Optional[float] = None
    balance: Optional[float] = None


@dataclass
class Row:
    row_id: int
    source: dict[str, Any] = field(default_factory=dict)
    raw: Raw = field(default_factory=Raw)
    fields: dict[str, Field] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
