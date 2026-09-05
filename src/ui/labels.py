"""Plain English for the review screen.

The user is a fund manager, not an engineer. Field keys, confidence floats and raw
currency codes are all internal vocabulary -- none of it should reach the screen.
Everything a reviewer sees is translated here, in one place, so the wording can be
changed without touching templates or logic.
"""
from __future__ import annotations

import re
from datetime import date

from markupsafe import Markup, escape

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


def statement_label(pdf_name: str, page: int | None = None) -> str:
    """'20260331_NI_V_SCSP_CALDER_EUR_030041.pdf' ->
    'NI V SCSP  ·  Calder EUR account ...0041  ·  statement of 31 Mar 2026, page 2'

    The reviewer needs to be able to open the actual statement and find this line. The
    filename is the only thing that gets them there, so it is translated rather than
    hidden -- and shown verbatim on hover."""
    stem = pdf_name[:-4] if pdf_name.lower().endswith(".pdf") else pdf_name
    parts = stem.split("_")
    if len(parts) < 4:
        return pdf_name
    raw_date, account = parts[0], parts[-1]
    currency, bank = parts[-2], parts[-3]
    entity = " ".join(parts[1:-3])
    try:
        when = pretty_date(f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}")
    except (ValueError, IndexError):
        when = raw_date
    tail = f", page {page}" if page else ""
    return (
        f"{entity}  ·  {bank.capitalize()} {currency} account \u2026{account[-4:]}"
        f"  ·  statement of {when}{tail}"
    )


def highlight(text: str, spans: list[tuple[int, int] | None]) -> Markup:
    """Wrap the evidence spans in <mark>. Spans index into the raw narrative, which is why
    normalisation keeps an index map -- see matcher/normalise.py.

    Overlapping spans are merged, and everything is escaped before any markup is added."""
    clean = [tuple(s) for s in spans if s and len(s) == 2 and s[1] > s[0]]
    if not clean:
        return Markup(escape(text))
    merged: list[list[int]] = []
    for start, end in sorted(clean):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    out, cursor = [], 0
    for start, end in merged:
        out.append(escape(text[cursor:start]))
        out.append(Markup("<mark>") + escape(text[start:end]) + Markup("</mark>"))
        cursor = end
    out.append(escape(text[cursor:]))
    return Markup("").join(out)
