"""The six Process-sheet stages, as pure functions over a Row.

Stage order matters: `Process` sheet says "each value is only as good as the stage
before it -- when something looks wrong, fix the earliest stage first."

Two stages are fully deterministic and should hit 100/100 in the first hour. Do those
before touching the hard ones, so there is always a working pipeline to demo.
"""
from __future__ import annotations

from src.contract import Evidence, Field, Row

# --------------------------------------------------------------------------- free


def matched_legal_entity(row: Row, legal_entities: list[str]) -> Field:
    """Account Name -> full legal entity. 100/100 achievable: it is a lookup against a
    99-row master list, with the bank's abbreviated form on one side."""
    raise NotImplementedError("W2: exact + abbreviation match on Legal Entity Master List")


def cash_leg_transtype(row: Row) -> Field:
    """`Cash - Received - {CCY}` or `Cash - Disbursed - {CCY}`. Fully determined by the
    currency and which of credit/debit is populated. No lookup, no model, no ambiguity."""
    direction = "Received" if (row.raw.credit or 0) > 0 else "Disbursed"
    value = f"Cash - {direction} - {row.raw.currency}"
    return Field(
        value=value,
        confidence=1.0,
        status="auto",
        evidence=Evidence(text=f"{direction.lower()} leg, {row.raw.currency}", source_list="derived"),
    )


# --------------------------------------------------------------------------- hard


def pulled_out_sender_beneficiary(row: Row) -> Field:
    """Stage 2. Pull the counterparty out of the narrative text.

    Human baseline: filled on 55 of 100 rows. Every string the staging sheet claims was
    pulled from a narrative is still literally present in the source PDF, in the bank's
    truncated uppercase form -- so this is extraction, not inference."""
    raise NotImplementedError("W2")


def matched_sender_beneficiary(row: Row, masters: dict[str, list[str]]) -> Field:
    """Stage 4. Match the pulled name against the master lists, in priority order:
    Related Party Master -> Legal Entity Master -> Investor Master -> Vendor Master.

    Human baseline: 48 of 100. The 52 blanks are the opportunity -- resolve what you can
    and mark the rest `unresolved` with alternatives, never a silent blank."""
    raise NotImplementedError("W2")


def matched_project_code(row: Row, project_codes: list[dict[str, str]]) -> Field:
    """Stage 3. Careful: this is not a plain lookup. In the ground truth, 30 of 100 rows
    carry the literal string 'Flag for review - no project match' and 26 carry
    'OH - Bank Fees'. Reproduce that vocabulary rather than leaving blanks."""
    raise NotImplementedError("W2")


def classification(row: Row) -> Field:
    """Stage 4. The Process sheet claims the vocabulary is
    Investment / Vendor / Related Party / Investor / Internal / Review.

    The data disagrees. Actual top values are 'Other' (32), 'Internal' (17),
    'Investment Transfer' (15). Trust the data, not the doc."""
    raise NotImplementedError("W2")


def resolved_position(row: Row, deals: list[dict[str, str]]) -> Field:
    """Stage 5. Position under the deal, from a 6,637-row master. Investments only --
    filled on 30 of 100 rows."""
    raise NotImplementedError("W2")
