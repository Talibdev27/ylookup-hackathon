"""The review queue's ordering.

Ordering is the only logic in the UI worth pinning: everything else it does is wording,
which `test_labels.py` covers.
"""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui.app import amount, flagged_discrepancy, queue_rank
from src.checks.contract import Flag


def row(row_id: int, *, credit=None, debit=None, cash_leg: str = "auto") -> dict:
    return {
        "row_id": row_id,
        "raw": {"credit": credit, "debit": debit},
        "fields": {"cash_leg_transtype": {"status": cash_leg}},
    }


def entry(r: dict) -> dict:
    return {"row": r, "questions": [], "answered": {}, "flags": []}


@contextmanager
def app_state(rows: list[dict], flags: list[dict]):
    from src.ui import app as ui

    paths = (ui.ROWS, ui.DECISIONS, ui.FLAGS, ui.FLAG_DECISIONS)
    saved = {path: path.read_bytes() if path.exists() else None for path in paths}
    ui.ROWS.parent.mkdir(parents=True, exist_ok=True)
    ui.ROWS.write_text(json.dumps(rows))
    ui.DECISIONS.unlink(missing_ok=True)
    ui.FLAGS.write_text(json.dumps({
        "checks_total": 1,
        "checks_applied": ["balance_continuity"],
        "check_failures": {},
        "flags_found": len(flags),
        "flags": flags,
    }))
    ui.FLAG_DECISIONS.unlink(missing_ok=True)
    try:
        yield ui, ui.app.test_client()
    finally:
        for path, content in saved.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)


def review_row(value: str = "Maybe Ltd") -> dict:
    return {
        "row_id": 1,
        "source": {"pdf": "statement.pdf", "page": 2},
        "raw": {
            "account_name": "NI V SCSP",
            "account_number": "ACC-1",
            "currency": "EUR",
            "narrative_raw": "PAYMENT TO MAYBE LTD",
            "value_date": "2026-03-31",
            "credit": None,
            "debit": -50.0,
        },
        "fields": {
            "matched_sender_beneficiary": {
                "value": value,
                "confidence": 0.5,
                "status": "needs_review",
                "evidence": {"span": [11, 20], "text": "please check this", "source_list": "Vendor list"},
                "alternatives": [],
            }
        },
    }


def review_flag(message: str = "the balance does not reconcile") -> dict:
    return asdict(Flag(
        check="balance_continuity",
        severity="error",
        message=message,
        source={"pdf": "statement.pdf", "page": 2, "row_id": 1},
        expected=100.0,
        actual=150.0,
    ))


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


def test_api_unifies_matcher_questions_and_flags_with_clear_counts() -> None:
    finding = review_flag()
    with app_state([review_row()], [finding]) as (_, client):
        response = client.get("/api/review")
        assert response.status_code == 200
        body = response.get_json()
        assert body["checks"]["checks_executed"] == 1
        assert body["summary"]["matcher_questions_remaining"] == 1
        assert body["summary"]["automated_flags_remaining"] == 1
        assert body["summary"]["total_review_items_remaining"] == 2
        assert len(body["items"]) == 1
        assert len(body["items"][0]["matcher_questions"]) == 1
        assert body["items"][0]["automated_flags"][0]["label"] == "Balance continuity"


def test_flag_decisions_validate_and_persist_independently() -> None:
    finding = review_flag()
    flag_id = finding["flag_id"]
    with app_state([review_row()], [finding]) as (ui, client):
        malformed = client.post(
            f"/api/flags/{flag_id}/decide", data="not json", content_type="text/plain"
        )
        assert malformed.status_code == 400 and ui.load_flag_decisions() == {}
        invalid = client.post(f"/api/flags/{flag_id}/decide", json={"action": "delete"})
        assert invalid.status_code == 400 and ui.load_flag_decisions() == {}
        missing = client.post("/api/flags/not-real/decide", json={"action": "acknowledge"})
        assert missing.status_code == 404 and ui.load_flag_decisions() == {}
        too_long = client.post(
            f"/api/flags/{flag_id}/decide",
            json={"action": "resolved", "note": "x" * 1001},
        )
        assert too_long.status_code == 400 and ui.load_flag_decisions() == {}

        saved = client.post(
            f"/api/flags/{flag_id}/decide",
            json={"action": "resolved", "note": "Bank supplied a corrected statement"},
        )
        assert saved.status_code == 200
        decision = ui.load_flag_decisions()[flag_id]
        assert decision["action"] == "resolved"
        assert decision["source"]["pdf"] == "statement.pdf"


def test_reset_clears_field_and_flag_decisions() -> None:
    finding = review_flag()
    with app_state([review_row()], [finding]) as (ui, client):
        ui.save_decisions({"1": {"matched_sender_beneficiary": {"choice": "approve"}}})
        ui.save_flag_decisions({finding["flag_id"]: {"action": "acknowledge"}})
        response = client.post("/reset")
        assert response.status_code == 302
        assert ui.load_decisions() == {}
        assert ui.load_flag_decisions() == {}


def test_failed_check_does_not_expose_exception_detail() -> None:
    with app_state([review_row()], []) as (ui, client):
        report = ui.load_flag_report()
        report["checks_applied"] = []
        report["check_failures"] = {"balance_continuity (SecretDatabaseError)": 1}
        ui.FLAGS.write_text(json.dumps(report))
        body = client.get("/api/review").get_json()
        html = client.get("/").get_data(as_text=True)
        assert body["checks"]["failed"] == [
            {"check": "balance_continuity", "label": "Balance continuity", "status": "failed"}
        ]
        assert "SecretDatabaseError" not in json.dumps(body)
        assert "SecretDatabaseError" not in html


def test_handled_document_flag_is_hidden_unless_completed_work_is_requested() -> None:
    finding = review_flag()
    finding["source"].pop("row_id")
    with app_state([review_row()], [finding]) as (ui, client):
        ui.save_flag_decisions({finding["flag_id"]: {"action": "acknowledge"}})
        assert client.get("/api/review").get_json()["unattached_flags"] == []
        assert len(client.get("/api/review?all=1").get_json()["unattached_flags"]) == 1


def test_review_html_escapes_flags_and_expands_long_values() -> None:
    value = "Review - multiple positions: " + "candidate | " * 140
    finding = review_flag("<script>alert('x')</script>, balance is wrong")
    with app_state([review_row(value)], [finding]) as (_, client):
        response = client.get("/")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "<script>alert('x')</script>" not in html
        assert "&lt;script&gt;alert" in html
        assert '<details class="long-value">' in html
        assert value in html, "the full value remains available for decisions and expansion"


def test_a_clean_check_is_not_presented_as_skipped() -> None:
    with app_state([review_row()], []) as (_, client):
        html = client.get("/").get_data(as_text=True)
        assert "No balance inconsistencies found" in html
        assert "Automated checks have not run" not in html


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all ui checks pass")
