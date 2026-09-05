"""The six Process-sheet stages, as pure functions over a Row.

Stage order matters: `Process` sheet says "each value is only as good as the stage
before it -- when something looks wrong, fix the earliest stage first."

Two stages are fully deterministic and should hit 100/100 in the first hour. Do those
before touching the hard ones, so there is always a working pipeline to demo.
"""
from __future__ import annotations

from typing import Callable

from src.contract import Alternative, Evidence, Field, Row
from src.matcher import counterparty
from src.matcher.abbreviations import expand
from src.matcher.reference import ReferenceLists

# Every stage has this shape. One row, the reference lists, one field out. A stage that
# is not written yet raises NotImplementedError; anything else it raises is a defect and
# the runner treats it as one.
Stage = Callable[[Row, ReferenceLists], Field]

# --------------------------------------------------------------------------- free


def matched_legal_entity(row: Row, lists: ReferenceLists) -> Field:
    """Account Name -> the full legal entity, from the 97-row master list.

    The bank abbreviates (`NI ABF II SCSP`); the master list spells it out. See
    matcher/abbreviations.py for the expansion. Alternatives are kept even when the
    top candidate is clear, because `NI V SCSP` also opens `... VI SCSp` and the
    reviewer should be able to see what was rejected.
    """
    candidates = expand(row.raw.account_name, lists.legal_entities)
    if not candidates:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(
                text=f"no entry in the fund list matches {row.raw.account_name!r}",
                source_list="Legal Entity Master List",
            ),
        )
    best = candidates[0]
    return Field(
        value=best.value,
        confidence=best.confidence,
        status="auto" if best.confidence >= 0.7 else "needs_review",
        evidence=Evidence(
            text=f"the account is named {row.raw.account_name!r} on the statement",
            source_list="Legal Entity Master List",
        ),
        alternatives=[
            Alternative(value=other.value, confidence=other.confidence)
            for other in candidates[1:4]
        ],
    )


def cash_leg_transtype(row: Row, lists: ReferenceLists) -> Field:
    """The cash side of the journal, in the row currency.

    The Process sheet documents the rule as "Cash - Received or Cash - Disbursed in the
    row currency, matching the credit or debit side."

    The ground truth does not do that. All 100 rows are booked `Cash - Disbursed`,
    including the 23 where money came in. We reproduce the data, because the data is what
    the target system received -- but we flag every row where the documented rule and the
    actual booking disagree, with the reason attached, and let a human decide.

    That disagreement is the product: it is the "nobody checks whether this number foots
    to that number" problem from the interview, sitting in their own working file.
    """
    incoming = (row.raw.credit or 0) > 0
    value = f"Cash - Disbursed - {row.raw.currency}"
    if not incoming:
        return Field(
            value=value,
            confidence=1.0,
            status="auto",
            evidence=Evidence(text=f"debit row, {row.raw.currency}", source_list="derived"),
        )
    return Field(
        value=value,
        confidence=0.6,
        status="needs_review",
        evidence=Evidence(
            text=(
                f"credit of {row.raw.credit:,.2f} {row.raw.currency}: the Process sheet "
                f"says a credit row books to Cash - Received, but every row in the "
                f"working file is booked Cash - Disbursed"
            ),
            source_list="Process sheet, stage 4",
        ),
        alternatives=[Alternative(value=f"Cash - Received - {row.raw.currency}", confidence=0.4)],
    )


# --------------------------------------------------------------------------- hard


def pulled_out_sender_beneficiary(row: Row, lists: ReferenceLists) -> Field:
    """Stage 2. The counterparty as the bank wrote it, with its span in the narrative.

    Human baseline: filled on 55 of 100 rows. Every string the staging sheet claims was
    pulled from a narrative is still literally present in the source PDF, so this is
    extraction rather than inference -- and the span is what the review screen highlights.
    """
    found = counterparty.extract(row.raw.narrative_raw)
    if not found:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(text="no name found in the bank text", source_list="Narrative"),
        )
    fragment, span = found
    value = counterparty.complete(fragment, row.raw.narrative_raw)
    truncated = value != fragment
    return Field(
        value=value,
        confidence=0.75 if truncated else 0.9,
        status="auto",
        evidence=Evidence(
            span=span,
            text=(
                "the bank cut this name off at a line break; the full form appears later "
                "in the same text"
                if truncated
                else "read from the bank text"
            ),
            source_list="Narrative",
        ),
    )


def matched_sender_beneficiary(row: Row, lists: ReferenceLists) -> Field:
    """Stage 4. The pulled name, matched against the reference lists.

    Human baseline: 48 of 100. The 52 they left blank are the opportunity, so an
    unmatched row is marked `unresolved` and carries whatever near misses were found --
    never a silent blank, which is what the fund manager is complaining about.
    """
    pulled = row.fields.get("pulled_out_sender_beneficiary")
    name = pulled.value if pulled else None
    if not name:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(text="no name was found in the bank text to look up"),
        )

    hits = counterparty.match(name, lists.counterparty_lists(), currency=row.raw.currency)
    if not hits:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(
                span=pulled.evidence.span if pulled else None,
                text=f"{name!r} is not on any of the reference lists",
                source_list="Related Party, Legal Entity, Investor and Vendor lists",
            ),
        )
    best = hits[0]
    return Field(
        value=best.value,
        confidence=best.confidence,
        status="auto" if best.confidence >= 0.85 else "needs_review",
        evidence=Evidence(
            span=pulled.evidence.span if pulled else None,
            text=f"the bank text names {name!r}",
            source_list=best.source_list,
        ),
        alternatives=[Alternative(value=h.value, confidence=h.confidence) for h in hits[1:4]],
    )


def matched_project_code(row: Row, lists: ReferenceLists) -> Field:
    """Stage 3. Careful: this is not a plain lookup. In the ground truth, 30 of 100 rows
    carry the literal string 'Flag for review - no project match' and 26 carry
    'OH - Bank Fees'. Reproduce that vocabulary rather than leaving blanks."""
    raise NotImplementedError("W2")


def classification(row: Row, lists: ReferenceLists) -> Field:
    """Stage 4. What kind of transaction this is.

    The Process sheet claims the vocabulary is Investment / Vendor / Related Party /
    Investor / Internal / Review. The data disagrees: there is no `Investor` at all, and
    `Other` (32) and `Investment Transfer` (15) both appear. VOCABULARY is the data's.

    The handle is that classification largely tracks *which reference list the
    counterparty matched against*, which `matched_sender_beneficiary` has already
    recorded. Three of those lists answer the question outright, measured on the 100
    ground-truth rows:

        Deal & Position Master List  ->  Investment      6 / 6
        Investor Master List         ->  Related Party   5 / 5
        Vendor Master List           ->  Vendor          6 / 7

    `Investor Master List -> Related Party` reads wrong and is not. These are the fund's
    own feeder vehicles: they are listed as investors and booked as related parties.

    The other two outcomes -- matched in `Related Party Master`, or matched nowhere at
    all -- carry 82 of the 100 rows and split four ways each. Those are the narrative's
    job, and until that is written they go to a reviewer rather than take the majority
    value: guessing `Other` would score well and lie about it.
    """
    matched = row.fields.get("matched_sender_beneficiary")
    source = matched.evidence.source_list if matched and matched.value else ""

    decisive = {
        "Deal & Position Master List": ("Investment", "the deal list"),
        "Investor Master List": ("Related Party", "the investor list"),
        "Vendor Master List": ("Vendor", "the vendor list"),
    }
    if source in decisive:
        value, where = decisive[source]
        return Field(
            value=value,
            confidence=0.9,
            status="auto",
            evidence=Evidence(
                span=matched.evidence.span,
                text=f"{matched.value!r} is on {where}",
                source_list=source,
            ),
        )

    reason = (
        f"{matched.value!r} is a related party, and related parties are booked several "
        "different ways depending on what the payment was for"
        if source
        else "we could not tell who this was to or from, so we cannot say what kind of "
        "transaction it is"
    )
    return Field(
        value=None,
        confidence=0.0,
        status="needs_review",
        evidence=Evidence(
            span=matched.evidence.span if matched else None,
            text=reason,
            source_list=source or "Narrative",
        ),
    )


def resolved_position(row: Row, lists: ReferenceLists) -> Field:
    """Stage 5. Position under the deal, from a 6,637-row master. Investments only --
    filled on 30 of 100 rows."""
    raise NotImplementedError("W2")


def pulled_out_project_code(row: Row, lists: ReferenceLists) -> Field:
    """Stage 3. The project word as the bank wrote it. Filled on 25 of 100 rows."""
    raise NotImplementedError("W2")


def counterparty_transtype(row: Row, lists: ReferenceLists) -> Field:
    """Stage 4. The account the counterpart line books to. Filled on all 100 rows, and
    26 of them are just `Expense - Bank Charges`. Rows booked to Suspense are the ones
    the Process sheet asks a reviewer to investigate."""
    raise NotImplementedError("W2")


def resolved_deal(row: Row, lists: ReferenceLists) -> Field:
    """Stage 5. The deal a position sits under. Filled on 30 of 100 rows, and falls out
    of resolved_position -- the deal master carries both columns on one row."""
    raise NotImplementedError("W2")


# The stages in the order the Process sheet runs them. This list is the registry: adding
# a stage means adding a function above and a line here, in one file.
#
# The order is load-bearing. matched_sender_beneficiary reads the field that
# pulled_out_sender_beneficiary writes, so it has to come after it. That constraint used
# to survive only as dict insertion order in another module; tests/test_stages.py now
# asserts it.
REGISTRY: list[tuple[str, Stage]] = [
    ("matched_legal_entity", matched_legal_entity),
    ("pulled_out_project_code", pulled_out_project_code),
    ("matched_project_code", matched_project_code),
    ("pulled_out_sender_beneficiary", pulled_out_sender_beneficiary),
    ("matched_sender_beneficiary", matched_sender_beneficiary),
    ("classification", classification),
    ("cash_leg_transtype", cash_leg_transtype),
    ("counterparty_transtype", counterparty_transtype),
    ("resolved_deal", resolved_deal),
    ("resolved_position", resolved_position),
]
