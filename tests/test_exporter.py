"""Turning a reviewed queue into a file.

The point of the column pairs is auditability: a fund manager receiving this has to be
able to tell which answers a person stood behind and which the machine produced alone.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.exporter import summary, to_csv


def a_row(row_id: int, **fields) -> dict:
    return {
        "row_id": row_id,
        "source": {"pdf": "statement.pdf", "page": 1},
        "raw": {
            "account_name": "NI V SCSP",
            "account_number": "240-1",
            "currency": "EUR",
            "value_date": "2026-03-31",
            "credit": None,
            "debit": -1041.13,
            "narrative_raw": "TRENTBECK AUDIT LUXEMBOURG",
        },
        "fields": fields,
    }


def field(value, status="auto"):
    return {"value": value, "status": status, "confidence": 0.9}


def flag(flag_id: str, row_id: int, message: str = "balance does not reconcile") -> dict:
    return {
        "flag_id": flag_id,
        "check": "balance_continuity",
        "severity": "error",
        "message": message,
        "source": {"pdf": "statement.pdf", "page": 1, "row_id": row_id},
        "expected": 150.0,
        "actual": 200.0,
    }


def parse(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def test_a_confident_answer_is_attributed_to_the_matcher() -> None:
    rows = [a_row(1, matched_sender_beneficiary=field("Trentbeck Audit - Lu"))]
    out = parse(to_csv(rows, {}))[0]
    assert out["Counterparty"] == "Trentbeck Audit - Lu"
    assert out["Counterparty — decided by"] == "matcher"


def test_an_unsure_answer_says_so_rather_than_passing_as_settled() -> None:
    rows = [a_row(1, matched_sender_beneficiary=field("Maybe Ltd", status="needs_review"))]
    out = parse(to_csv(rows, {}))[0]
    assert out["Counterparty"] == "Maybe Ltd"
    assert out["Counterparty — decided by"] == "matcher: needs_review"


def test_a_reviewer_overrides_the_matcher() -> None:
    rows = [a_row(1, matched_sender_beneficiary=field("Wrong Ltd"))]
    decisions = {"1": {"matched_sender_beneficiary": {"choice": "manual", "value": "NIP P/S"}}}
    out = parse(to_csv(rows, decisions))[0]
    assert out["Counterparty"] == "NIP P/S"
    assert out["Counterparty — decided by"] == "reviewer: manual"


def test_could_not_tell_clears_the_value() -> None:
    """A reviewer who gives up has rejected the proposal. Falling back to it would ship a
    guess they already turned down."""
    rows = [a_row(1, matched_sender_beneficiary=field("A Guess Ltd", status="needs_review"))]
    decisions = {"1": {"matched_sender_beneficiary": {"choice": "unresolved", "value": ""}}}
    out = parse(to_csv(rows, decisions))[0]
    assert out["Counterparty"] == ""
    assert out["Counterparty — decided by"] == "reviewer: could not tell"


def test_the_statement_it_came_from_travels_with_the_row() -> None:
    out = parse(to_csv([a_row(1, matched_legal_entity=field("Nordvik Infrastructure V SCSp"))], {}))[0]
    assert out["Statement"] == "statement.pdf" and out["Page"] == "1"
    assert out["Bank narrative"] == "TRENTBECK AUDIT LUXEMBOURG"


def test_columns_appear_only_for_fields_the_matcher_produced() -> None:
    """A column the matcher produced nothing for is left out rather than left empty.

    An empty column implies the answer was looked at and left blank, which is a different
    claim from never having been asked -- the same distinction the review queue draws on
    screen. It mattered most when six stages were unwritten; it still holds for a row
    where a stage declined to answer."""
    text = to_csv([a_row(1, matched_legal_entity=field("Nordvik Infrastructure V SCSp"))], {})
    header = text.splitlines()[0]
    assert "Fund" in header
    assert "Deal" not in header


def test_summary_counts_rows_not_fields() -> None:
    rows = [
        a_row(1, a=field("x", status="needs_review"), b=field("y", status="needs_review")),
        a_row(2, a=field("x", status="needs_review")),
        a_row(3, a=field("x")),
    ]
    counts = summary(rows, {"1": {"a": {"choice": "approve", "value": "x"}}})
    assert counts["rows"] == 3
    assert counts["outstanding"] == 2, "row 1 has an unanswered field, row 2 is untouched"
    assert counts["reviewed"] == 0


def test_check_findings_and_their_disposition_travel_with_the_row() -> None:
    rows = [a_row(1, matched_sender_beneficiary=field("NIP P/S"))]
    findings = [flag("flag-1", 1, "balance is wrong,\nand needs review")]
    flag_decisions = {"flag-1": {"action": "resolved", "note": "Bank confirmed, fixed"}}
    out = parse(to_csv(rows, {}, findings, flag_decisions))[0]
    assert out["Check findings"] == "balance is wrong,\nand needs review"
    assert out["Check severity"] == "error"
    assert out["Check expected"] == "150.0" and out["Check actual"] == "200.0"
    assert out["Check review action"] == "resolved"
    assert out["Check reviewer note"] == "Bank confirmed, fixed"


def test_multiple_flags_export_in_stable_id_order() -> None:
    rows = [a_row(1)]
    findings = [flag("z-last", 1, "second"), flag("a-first", 1, "first")]
    out = parse(to_csv(rows, {}, findings, {}))[0]
    assert out["Check findings"] == "first\nsecond"


def test_field_and_flag_decisions_are_independent() -> None:
    rows = [a_row(1, matched_sender_beneficiary=field("Wrong", status="needs_review"))]
    field_decisions = {
        "1": {"matched_sender_beneficiary": {"choice": "manual", "value": "NIP P/S"}}
    }
    flag_decisions = {"flag-1": {"action": "false_positive", "note": "Statement corrected"}}
    out = parse(to_csv(rows, field_decisions, [flag("flag-1", 1)], flag_decisions))[0]
    assert out["Counterparty"] == "NIP P/S"
    assert out["Counterparty — decided by"] == "reviewer: manual"
    assert out["Check review action"] == "false_positive"


def test_summary_counts_questions_flags_and_transactions_separately() -> None:
    rows = [
        a_row(1, a=field("x", status="needs_review"), b=field("y", status="needs_review")),
        a_row(2, a=field("x")),
    ]
    findings = [flag("flag-1", 1), flag("flag-2", 2)]
    counts = summary(
        rows,
        {"1": {"a": {"choice": "approve", "value": "x"}}},
        findings,
        {"flag-2": {"action": "acknowledge"}},
    )
    assert counts["matcher_questions_total"] == 2
    assert counts["matcher_questions_remaining"] == 1
    assert counts["automated_flags_found"] == 2
    assert counts["automated_flags_remaining"] == 1
    assert counts["total_review_items_remaining"] == 2
    assert counts["outstanding"] == 1 and counts["reviewed"] == 1


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all exporter checks pass")
