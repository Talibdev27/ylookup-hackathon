"""Plain English for the review screen.

The user is a fund manager, not an engineer. Field keys, confidence floats and raw
currency codes are all internal vocabulary -- none of it should reach the screen.
Everything a reviewer sees is translated here, in one place, so the wording can be
changed without touching templates or logic.
"""
from __future__ import annotations

from datetime import date

# Field key -> (what to call it, what the reviewer is actually being asked)
FIELD_LABELS: dict[str, tuple[str, str]] = {
    "matched_legal_entity": ("Fund", "Which fund does this transaction belong to?"),
    "pulled_out_project_code": ("Project mentioned", "Which project does the bank text name?"),
    "matched_project_code": ("Project code", "Which project code should this be booked to?"),
    "pulled_out_sender_beneficiary": ("Name in the bank text", "Who does the bank say this was to or from?"),
    "matched_sender_beneficiary": ("Counterparty", "Who was this actually paid to, or received from?"),
    "classification": ("Type of transaction", "What kind of transaction is this?"),
    "cash_leg_transtype": ("Cash side of the entry", "How should the cash side be booked?"),
    "counterparty_transtype": ("Other side of the entry", "What account does the other side go to?"),
    "resolved_deal": ("Deal", "Which deal is this under?"),
    "resolved_position": ("Position", "Which position under that deal?"),
}

SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "DKK": "kr "}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def label(field_key: str) -> str:
    return FIELD_LABELS.get(field_key, (field_key.replace("_", " ").capitalize(), ""))[0]


def question(field_key: str) -> str:
    return FIELD_LABELS.get(field_key, ("", "Is this right?"))[1]


def money(amount: float | None, currency: str) -> str:
    """-301908.7, 'EUR' -> '€301,908.70'. Direction is carried by wording, not a sign:
    a minus in front of a number is easy to miss and easy to misread."""
    if amount is None:
        return ""
    return f"{SYMBOLS.get(currency, currency + ' ')}{abs(amount):,.2f}"


def direction(credit: float | None, debit: float | None) -> str:
    return "Money in" if (credit or 0) > 0 else "Money out"


def pretty_date(iso: str | None) -> str:
    """'2026-03-31' -> '31 Mar 2026'."""
    if not iso:
        return ""
    try:
        parsed = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{parsed.day} {MONTHS[parsed.month - 1]} {parsed.year}"


def certainty(confidence: float, status: str) -> str:
    """Words, not a number. 0.60 tells a fund manager nothing."""
    if status == "unresolved":
        return "Could not work this out"
    if status == "auto":
        return "Confident"
    if confidence >= 0.75:
        return "Fairly confident"
    return "Not sure — please check"
