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


def test_the_counterparty_is_the_party_that_is_not_this_account() -> None:
    """On a transfer between two of the fund's own vehicles the bank leads with an alias
    of the account the statement belongs to, so the leading name is the wrong answer."""
    row = a_row(
        account_name="NI ABF I SCSP",
        narrative_raw="NORDVIK I.A.B. FUND I, TFR+ PMT FRM NI ABF II SCSP TO NI ABF I, SCSP FOR ACQ",
    )
    lists = ReferenceLists(related_parties=["NI ABF II SCSp", "NI ABF I SCSp"])
    result = stages.pulled_out_sender_beneficiary(row, lists)
    assert result.value == "NI ABF II SCSP", "the payer, not the account being read"
    start, end = result.evidence.span
    assert row.raw.narrative_raw[start:end] == "NI ABF II SCSP"


def test_a_leading_name_that_is_identifiable_is_left_alone() -> None:
    """The rule above only fires when the name we read is on none of the lists. A
    narrative that names its counterparty up front must not be second-guessed."""
    row = a_row()
    assert stages.pulled_out_sender_beneficiary(row, LISTS).value == "TRENTBECK AUDIT LUXEMBOURG"


def test_a_different_legal_form_is_the_same_company() -> None:
    """`LTD` against `Limited` defeats every comparison in `match`: not equal, neither
    opens the other, and the token overlap breaks on the last word."""
    row = a_row(narrative_raw="NI V AZURITE HOLDCO LTD, 24370KF00HEC, /GB14NRVB35403891305213")
    lists = ReferenceLists(related_parties=["NI V Azurite HoldCo Limited"])
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, lists)
    assert stages.matched_sender_beneficiary(row, lists).value == "NI V Azurite HoldCo Limited"


def test_the_deal_master_settles_a_spelling_the_lists_disagree_about() -> None:
    """38 entities sit on more than one sheet spelled differently. Only the spelling
    moves -- the list it was found on is what `classification` reads, so that stays."""
    row = a_row(narrative_raw="52443473437109, NI DRACONIS HOLDCO I SCSP")
    lists = ReferenceLists(
        related_parties=["NI DRACONIS HOLDCO I SCSp"],
        deal_names=["NI Draconis HoldCo I SCSp"],
    )
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, lists)
    result = stages.matched_sender_beneficiary(row, lists)
    assert result.value == "NI Draconis HoldCo I SCSp", "the deal master's spelling"
    assert result.evidence.source_list == "Related Party Master", "but found on the related parties"


def test_the_same_entity_written_short_or_long_is_one_counterparty() -> None:
    """The group writes its own entities both ways and the sheets disagree about which.
    Both directions resolve, and the Process sheet's list order decides the spelling."""
    row = a_row(narrative_raw="52443473437109, NI ABF II SCSP")
    lists = ReferenceLists(
        related_parties=["Nordvik Infrastructure Advanced Bioenergy Fund II SCSp"],
    )
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, lists)
    spelled_out = stages.matched_sender_beneficiary(row, lists)
    assert spelled_out.value == "Nordvik Infrastructure Advanced Bioenergy Fund II SCSp"

    # ... and the other way round: the statement spells it out, the sheet abbreviates.
    row = a_row(narrative_raw="52443473437109, NORDVIK INFRASTRUCTURE V CN SCSP")
    lists = ReferenceLists(
        related_parties=["NI V CN SCSp"],
        legal_entities=["Nordvik Infrastructure V CN SCSp"],
    )
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, lists)
    shortened = stages.matched_sender_beneficiary(row, lists)
    assert shortened.value == "NI V CN SCSp", "the related party master outranks the entity list"


def test_a_roman_numeral_is_not_an_initial() -> None:
    """`I` opens `II`, so a loose initialism check quietly resolves fund I to fund II.
    An initialism token stands for two or more words, or is a word outright."""
    row = a_row(narrative_raw="52443473437109, NI ABF II SCSP")
    lists = ReferenceLists(related_parties=["NI ABF I SCSp"])
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, lists)
    assert stages.matched_sender_beneficiary(row, lists).value != "NI ABF I SCSp"


def test_classification_reads_the_list_the_counterparty_matched_against() -> None:
    """A vendor is a Vendor. The stage never looks at the name, only at where it was
    found -- which is the whole reason `matched_sender_beneficiary` records the list."""
    row = a_row()
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, LISTS)
    row.fields["matched_sender_beneficiary"] = stages.matched_sender_beneficiary(row, LISTS)
    result = stages.classification(row, LISTS)
    assert result.value == "Vendor" and result.status == "auto"


def test_classification_asks_rather_than_guessing_the_majority_value() -> None:
    """`Other` is the most common answer on 32 of 100 rows, so returning it whenever we
    cannot tell would score well and lie to the reviewer about how it got there."""
    row = a_row(narrative_raw="SOMEBODY ENTIRELY UNKNOWN LTD")
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, LISTS)
    row.fields["matched_sender_beneficiary"] = stages.matched_sender_beneficiary(row, LISTS)
    result = stages.classification(row, LISTS)
    assert result.value is None and result.status == "needs_review"


def test_classification_reads_what_the_bank_says_the_payment_was_for() -> None:
    """With no counterparty to go on, the narrative decides -- and the phrase that
    decided it is highlighted on the raw text the reviewer is looking at."""
    row = a_row(narrative_raw="CHARGES FOR 2, OUTWARD SEPA PAYMENT")
    row.fields["matched_sender_beneficiary"] = stages.matched_sender_beneficiary(row, LISTS)
    result = stages.classification(row, LISTS)
    assert result.value == "Other" and result.status == "auto"
    start, end = result.evidence.span
    assert row.raw.narrative_raw[start:end] == "CHARGES FOR"


def test_a_fee_line_that_also_waives_a_charge_is_still_a_fee() -> None:
    """Rule order is the rule. `CHARGE WAIVED` marks the fund's own transfers, but it
    also appears on fee lines, so the fee test has to run first."""
    row = a_row(narrative_raw="COMMISSION EUR 6,00, 47223IZ05W0Z CHARGE WAIVED")
    row.fields["matched_sender_beneficiary"] = stages.matched_sender_beneficiary(row, LISTS)
    assert stages.classification(row, LISTS).value == "Other"


def test_counterparty_transtype_follows_the_kind_and_the_direction() -> None:
    """Same vendor, same narrative, opposite sign. The account is a consequence of the
    classification and which way the money went, not a separate question."""
    row = a_row()
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, LISTS)
    row.fields["matched_sender_beneficiary"] = stages.matched_sender_beneficiary(row, LISTS)
    row.fields["classification"] = stages.classification(row, LISTS)
    result = stages.counterparty_transtype(row, LISTS)
    assert result.value == "Accounts Payable" and result.status == "auto"
    assert result.alternatives, "the reviewer is given the other side to pick from"


def test_a_suspense_row_goes_to_a_reviewer_however_clear_the_rule_is() -> None:
    """`Suspense` is not an answer. It is the Process sheet parking a row for somebody
    to investigate, so it never books through unseen."""
    row = a_row(narrative_raw="NI V SCSP, 22801YB03UF8, INTERNAL TRANSFER")
    row.fields["matched_sender_beneficiary"] = stages.matched_sender_beneficiary(row, LISTS)
    row.fields["classification"] = stages.classification(row, LISTS)
    result = stages.counterparty_transtype(row, LISTS)
    assert result.value == "Suspense (debit)" and result.status == "needs_review"


def test_counterparty_transtype_inherits_the_doubt_of_the_stage_before_it() -> None:
    """The Process sheet's own rule: each value is only as good as the stage before it."""
    row = a_row(narrative_raw="SOMEBODY ENTIRELY UNKNOWN LTD")
    row.fields["pulled_out_sender_beneficiary"] = stages.pulled_out_sender_beneficiary(row, LISTS)
    row.fields["matched_sender_beneficiary"] = stages.matched_sender_beneficiary(row, LISTS)
    row.fields["classification"] = stages.classification(row, LISTS)
    result = stages.counterparty_transtype(row, LISTS)
    assert result.value is None and result.status == "needs_review"


PROJECTS = ReferenceLists(
    project_codes=[{"Project Code": "Azurite Array"}, {"Project Code": "Cephalus"},
                   {"Project Code": "NIP Platform Solutions ApS"}],
)


def test_matched_project_code_recovers_the_reports_own_spelling() -> None:
    """The bank writes AZURITE, the project report carries `Azurite Array`."""
    row = a_row(narrative_raw="EQUITY: FROM NI V SCSP TO NI V AZURITE HOLDCO LTD. PROJECT AZURITE.")
    assert stages.pulled_out_project_code(row, PROJECTS).value == "AZURITE"
    assert stages.matched_project_code(row, PROJECTS).value == "Azurite Array"


def test_a_project_named_across_a_line_break_is_still_named() -> None:
    """The bank wraps mid-phrase and leaves a comma at the wrap point, so `PROJECT,
    RANFJORD II.` is one phrase broken in two rather than a project called nothing."""
    row = a_row(narrative_raw="NI RANFJORD II SCSP, 25515MS49ERZ, EQUITY: ... PROJECT, RANFJORD II.")
    lists = ReferenceLists(project_codes=[{"Project Code": "Ranfjord"},
                                          {"Project Code": "Ranfjord II"}])
    assert stages.pulled_out_project_code(row, lists).value == "RANFJORD II"
    assert stages.matched_project_code(row, lists).value == "Ranfjord II", "not the shorter Ranfjord"


def test_a_bank_fee_books_to_overhead_without_a_lookup() -> None:
    """31 rows have no project because the counterparty is the bank itself."""
    row = a_row(narrative_raw="CHARGES FOR 2, OUTWARD SEPA PAYMENT")
    assert stages.matched_project_code(row, PROJECTS).value == "OH - Bank Fees"


def test_a_project_code_in_the_payee_position_is_not_a_project() -> None:
    """Several project codes are also counterparty names. Without the guard, a payee
    called NIP Platform Solutions ApS is read as the project it was booked against, and
    a row the human flagged comes back with a confident wrong code."""
    row = a_row(narrative_raw="29000231,84819265, NIP PLATFORM SOLUTIONS APS")
    result = stages.matched_project_code(row, PROJECTS)
    assert result.value == "Flag for review - no project match"


def test_flagging_for_review_is_an_answer_not_a_blank() -> None:
    """30 of the 100 rows carry this literal string. It is the sheet's way of saying a
    human has to pick, so the stage says it out loud rather than leaving the cell empty."""
    row = a_row(narrative_raw="52443473437109-3528152584, TRENTBECK AUDIT LUXEMBOURG")
    result = stages.matched_project_code(row, PROJECTS)
    assert result.value == "Flag for review - no project match"
    assert result.status == "needs_review"


DEALS = ReferenceLists(
    legal_entities=["Nordvik Infrastructure V SCSp"],
    related_parties=["NI V Azurite HoldCo Limited"],
    deal_names=["NI V Azurite HoldCo Limited"],
    project_codes=[{"Project Code": "Azurite Array"}],
    deals=[
        {"Legal Entity": "Nordvik Infrastructure V SCSp", "Deal Name": "NI V Azurite HoldCo Limited",
         "Position": "NI V Azurite HoldCo Limited (Pallas Wind Limited (Azurite Array (Equity)))",
         "Security Type": "Equity"},
        {"Legal Entity": "Nordvik Infrastructure V SCSp", "Deal Name": "NI V Azurite HoldCo Limited",
         "Position": "NI V Azurite HoldCo Limited (Pallas Wind Limited (Azurite Array (Funding loan)))",
         "Security Type": "Funding loan"},
    ],
)


def _through_to_the_deal(row):
    """Drive the stages the deal pair reads, in registry order."""
    for name in ("matched_legal_entity", "pulled_out_project_code", "matched_project_code",
                 "pulled_out_sender_beneficiary", "matched_sender_beneficiary", "classification",
                 "resolved_deal"):
        row.fields[name] = dict(stages.REGISTRY)[name](row, DEALS)
    return row


def test_a_bank_fee_has_no_deal_behind_it() -> None:
    """Only an investment has a deal. Every one of the 30 rows the human gave a deal is
    classified Investment or Investment Transfer, so everything else says nothing rather
    than reaching for the nearest name in a 6,635-row master."""
    row = _through_to_the_deal(a_row(narrative_raw="CHARGES FOR 2, OUTWARD SEPA PAYMENT"))
    assert row.fields["resolved_deal"].value is None
    assert stages.resolved_position(row, DEALS).value is None


def test_the_deal_is_the_counterparty_on_an_investment() -> None:
    row = _through_to_the_deal(a_row(
        narrative_raw="NI V AZURITE HOLDCO LTD, 24370KF00HEC, EQUITY: PROJECT AZURITE."))
    assert row.fields["resolved_deal"].value == "NI V Azurite HoldCo Limited"


def test_the_security_the_bank_bought_picks_the_position() -> None:
    """Two positions sit under the deal, one equity and one loan, and the narrative says
    which was bought."""
    row = _through_to_the_deal(a_row(
        narrative_raw="NI V AZURITE HOLDCO LTD, 24370KF00HEC, EQUITY: PROJECT AZURITE."))
    result = stages.resolved_position(row, DEALS)
    assert result.value.endswith("(Azurite Array (Equity)))") and result.status == "auto"


def test_positions_that_fit_equally_well_go_to_a_reviewer_together() -> None:
    """When the bank text does not say which security was bought, both candidates go up
    under the human's own heading rather than one being picked at random."""
    row = _through_to_the_deal(a_row(
        narrative_raw="NI V AZURITE HOLDCO LTD, 24370KF00HEC, PAYMENT FROM NORDVIK "
                      "INFRASTRUCTURE V SCSP TO NI V AZURITE HOLDCO LTD. PROJECT AZURITE."))
    assert row.fields["resolved_deal"].value == "NI V Azurite HoldCo Limited"
    result = stages.resolved_position(row, DEALS)
    assert result.value.startswith("Review - multiple positions: ")
    assert result.status == "needs_review" and len(result.alternatives) == 2


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
    """Every stage is written now, so this drives a declared-unwritten one directly.
    Naming a real stage here meant the test lost its subject each time one landed."""
    def unwritten_stage(row, lists):
        raise NotImplementedError("not written yet")

    original = list(stages.REGISTRY)
    stages.REGISTRY[:] = [("resolved_position", unwritten_stage)]
    try:
        payload = [{"row_id": 1, "source": {}, "raw": a_row().raw.__dict__.copy(), "fields": {}}]
        _, unwritten, failures = apply_stages(payload, LISTS)
    finally:
        stages.REGISTRY[:] = original

    assert unwritten == ["resolved_position"]
    assert not failures, "declaring a stage unwritten is not a failure"


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
