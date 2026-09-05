"""The stage seam.

Before every stage had the same shape there was no test here at all: each one took
different arguments, so driving them from a test meant bespoke wiring per stage. One
shape means one helper drives any of them, which is the leverage this seam buys.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.contract import Raw, Row
from src.matcher import stages
from src.matcher.reference import ReferenceLists
from src.matcher.run import apply_stages

# The in-memory adapter. Three lines, against a 6,635-row workbook -- and it is the
# second adapter at this seam, which is what makes the seam real rather than hypothetical.
LISTS = ReferenceLists(
    legal_entities=["Nordvik Infrastructure V SCSp"],
    related_parties=["NIP PLATFORM SOLUTIONS APS"],
    vendors=["Trentbeck Audit - Lu"],
)


def a_row(**overrides) -> Row:
    raw = {
        "account_name": "NI V SCSP",
        "currency": "EUR",
        "narrative_raw": "52443473437109-3528152584, TRENTBECK AUDIT LUXEMBOURG",
        "debit": -1041.13,
        **overrides,
    }
    return Row(row_id=1, source={"pdf": "test.pdf", "page": 1}, raw=Raw(**raw))


# --------------------------------------------------------------- (i) each live stage


def test_matched_legal_entity_expands_the_account_name() -> None:
    result = stages.matched_legal_entity(a_row(), LISTS)
    assert result.value == "Nordvik Infrastructure V SCSp"
    assert result.status == "auto"
    assert result.evidence.source_list == "Legal Entity Master List"


def test_cash_leg_transtype_flags_a_credit_against_the_documented_rule() -> None:
    debit = stages.cash_leg_transtype(a_row(), LISTS)
    assert debit.value == "Cash - Disbursed - EUR" and debit.status == "auto"
    credit = stages.cash_leg_transtype(a_row(credit=6550000.0, debit=None), LISTS)
    assert credit.value == "Cash - Disbursed - EUR", "the data books every row Disbursed"
    assert credit.status == "needs_review", "but the Process sheet says Received"


def test_pulled_out_sender_beneficiary_spans_the_raw_narrative() -> None:
    row = a_row()
    result = stages.pulled_out_sender_beneficiary(row, LISTS)
    assert result.value == "TRENTBECK AUDIT LUXEMBOURG"
    start, end = result.evidence.span
    assert row.raw.narrative_raw[start:end] == "TRENTBECK AUDIT LUXEMBOURG"


def test_matched_sender_beneficiary_reads_the_stage_before_it() -> None:
    row = a_row()
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, LISTS)
    result = stages.matched_sender_beneficiary(row, LISTS)
    assert result.value == "Trentbeck Audit - Lu", "master lists carry office suffixes"


def test_an_unknown_counterparty_is_unresolved_rather_than_guessed() -> None:
    row = a_row(narrative_raw="SOMEBODY ENTIRELY UNKNOWN LTD")
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, LISTS)
    result = stages.matched_sender_beneficiary(row, LISTS)
    assert result.value is None and result.status == "unresolved"


# ------------------------------------------- (ii) the defect that started the refactor


def test_a_broken_stage_is_a_failure_not_an_unwritten_stage(monkeypatch=None) -> None:
    """The regression test for the bug this refactor exists to fix.

    The old runner caught TypeError alongside NotImplementedError, so a genuine crash
    inside a working stage was reported as "not implemented yet" and the column scored
    0/100 while reading as honest incomplete work.
    """
    def exploding(row, lists):
        return "a" + 1  # TypeError, deep inside a stage that is very much written

    original = list(stages.REGISTRY)
    stages.REGISTRY[:] = [("cash_leg_transtype", exploding)]
    try:
        payload = [{"row_id": 1, "source": {}, "raw": a_row().raw.__dict__.copy(), "fields": {}}]
        rows, unwritten, failures = apply_stages(payload, LISTS)
    finally:
        stages.REGISTRY[:] = original

    assert "cash_leg_transtype" not in unwritten, "a crash is not a missing stage"
    assert failures["cash_leg_transtype"] == 1
    field = rows[0]["fields"]["cash_leg_transtype"]
    assert field["status"] == "unresolved", "the row survives for a human to look at"
    assert "TypeError" in field["evidence"]["source_list"], "the detail is kept"
    assert "TypeError" not in field["evidence"]["text"], "but never shown to a fund manager"


def test_an_unwritten_stage_is_reported_once_and_skipped() -> None:
    payload = [{"row_id": 1, "source": {}, "raw": a_row().raw.__dict__.copy(), "fields": {}}]
    _, unwritten, failures = apply_stages(payload, LISTS)
    assert "classification" in unwritten
    assert not failures


# ------------------------------------------------------- (iii) the ordering constraint


def test_the_registry_orders_pulled_out_before_matched() -> None:
    """matched_sender_beneficiary reads the field pulled_out_sender_beneficiary writes.
    That constraint used to survive only as dict insertion order in another module."""
    order = [name for name, _ in stages.REGISTRY]
    assert order.index("pulled_out_sender_beneficiary") < order.index("matched_sender_beneficiary")


def test_every_scored_column_has_a_stage() -> None:
    """Three columns used to be scored with no stage at all, so 0/100 could mean
    unwritten, unregistered or broken, with no way to tell which."""
    from src.contract import STAGING_COLUMN

    registered = {name for name, _ in stages.REGISTRY}
    assert not set(STAGING_COLUMN) - registered


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all stage checks pass")
