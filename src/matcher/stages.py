"""The six Process-sheet stages, as pure functions over a Row.

Stage order matters: `Process` sheet says "each value is only as good as the stage
before it -- when something looks wrong, fix the earliest stage first."

Two stages are fully deterministic and should hit 100/100 in the first hour. Do those
before touching the hard ones, so there is always a working pipeline to demo.
"""
from __future__ import annotations

import re
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
    narrative = row.raw.narrative_raw
    found = counterparty.extract(narrative)
    if found:
        fragment, span = found
        value = counterparty.strip_clause(counterparty.complete(fragment, narrative)) or fragment
        truncated = value != fragment

        # The leading name is the counterparty on most rows, and on a transfer between two
        # of the fund's own vehicles it is an alias of this very account. When the name we
        # read is on none of the lists but the text names two parties, the one that is not
        # this account is the better answer -- checked here rather than in the matching
        # stage, so both columns say the same thing about the same row.
        if not counterparty.match(value, lists.counterparty_lists(), currency=row.raw.currency):
            instead = counterparty.other_party(
                narrative, [row.raw.account_name, _own_legal_entity(row)]
            )
            if instead and counterparty.match(
                instead[0], lists.counterparty_lists(), currency=row.raw.currency
            ):
                return Field(
                    value=instead[0],
                    confidence=0.8,
                    status="auto",
                    evidence=Evidence(
                        span=instead[1],
                        text=(
                            "the bank text names two parties and this is the one that is "
                            "not this account"
                        ),
                        source_list="Narrative",
                    ),
                )
        return Field(
            value=value,
            confidence=0.75 if truncated else 0.9,
            status="auto",
            evidence=Evidence(
                span=span,
                text=(
                    "the bank cut this name off at a line break; the full form appears "
                    "later in the same text"
                    if truncated
                    else "read from the bank text"
                ),
                source_list="Narrative",
            ),
        )
    return Field(
        value=None,
        confidence=0.0,
        status="unresolved",
        evidence=Evidence(text="no name found in the bank text", source_list="Narrative"),
    )


def _own_legal_entity(row: Row) -> str:
    """The full name of the account this statement belongs to, if it has been worked out."""
    mine = row.fields.get("matched_legal_entity")
    return mine.value if mine and mine.value else ""


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
        # Nothing matched on the spelling. Before giving up, try again with the legal form
        # reduced -- `... TopCo Limited` and `... TOPCO LTD` are one company.
        loose = counterparty.match_by_legal_form(name, lists.counterparty_lists())
        if loose:
            return Field(
                value=loose.value,
                confidence=loose.confidence,
                status="auto",
                evidence=Evidence(
                    span=pulled.evidence.span if pulled else None,
                    text=(
                        f"the bank text names {name!r}, which is the same company written "
                        "with a different legal form"
                    ),
                    source_list=loose.source_list,
                ),
            )
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
        value=lists.canonical_spelling(best.value),
        confidence=best.confidence,
        status="auto" if best.confidence >= 0.85 else "needs_review",
        evidence=Evidence(
            span=pulled.evidence.span if pulled else None,
            text=f"the bank text names {name!r}",
            source_list=best.source_list,
        ),
        alternatives=[Alternative(value=h.value, confidence=h.confidence) for h in hits[1:4]],
    )


# The bank names a project in the clear: "... TO NI V AZURITE HOLDCO LTD. PROJECT AZURITE."
# Everything up to the full stop is the name; the sentence after it is the amount.
PROJECT_NAMED = re.compile(r"PROJECT[:\s]+([A-Z0-9][A-Z0-9\- ]*)")

# Overhead codes the bank's own wording settles, before any lookup happens. These are 31
# of the 100 rows and none of them names a project, because there is no project: the
# counterparty is the bank itself.
OVERHEAD_PHRASES = [
    (("CREDIT INTEREST",), "OH - Interest Income", "this is interest the bank paid"),
    (("COMMISSION", "CHARGES FOR"), "OH - Bank Fees", "this is a fee the bank charged"),
]

NO_PROJECT = "Flag for review - no project match"


def _named_project(narrative: str) -> str | None:
    """The project as the bank wrote it, from `PROJECT <name>`."""
    found = PROJECT_NAMED.search(" ".join(narrative.upper().split()))
    if not found:
        return None
    return found.group(1).split(".")[0].strip(" .,-") or None


def _lookup(word: str | None, codes: list[str]) -> str | None:
    """The project report's own spelling of a name the bank abbreviated.

    The bank writes `AZURITE`, the report carries `Azurite Array`; the shortest code the
    bank's word opens is the answer. Exact matches are preferred over prefixes so
    `Ranfjord` cannot be answered with `Ranfjord II`.
    """
    if not word:
        return None
    target = counterparty.fold(word)
    exact = [c for c in codes if counterparty.fold(c) == target]
    opened = [c for c in codes if counterparty.fold(c).startswith(target)]
    hits = exact or opened
    return min(hits, key=len) if hits else None


def _project_named_anywhere(narrative: str, codes: list[str]) -> str | None:
    """A project code written somewhere in the narrative other than as `PROJECT <name>`.

    Six rows name the project only in passing -- `... FOR ACQ 100PER OF SHARES IN
    CEPHALUS BIOGAS 001 LTD` -- so the `PROJECT` keyword misses them.

    The guard is the whole trick. Several project codes are also counterparty names, and
    without it `NIP PLATFORM SOLUTIONS APS` in the payee position gets read as a project:
    three rows the human flagged came back with a confident wrong code. So a code that
    only appears inside the counterparty is not a project reference. It costs the one row
    whose project really is its counterparty (`NI RANFJORD II SCSP`), which is the right
    side of that trade -- a missed code is flagged, a wrong one is booked.
    """
    found = counterparty.extract(narrative)
    payee = counterparty.fold(found[0]) if found else ""
    haystack = f" {counterparty.fold(narrative)} "
    for code in sorted(codes, key=lambda c: -len(counterparty.fold(c))):
        folded = counterparty.fold(code)
        if len(folded) < 5 or not folded[0].isalpha():
            continue  # too short or too numeric to be named by accident
        if f" {folded} " in haystack and (not payee or folded not in payee):
            return code
    return None


def matched_project_code(row: Row, lists: ReferenceLists) -> Field:
    """Stage 3. Which project code this books to.

    Not a plain lookup, and the vocabulary is the client's: 30 of the 100 rows carry the
    literal string `Flag for review - no project match`, which is an answer rather than a
    blank -- it is the sheet's way of saying a human has to pick. Reproducing it is the
    point, so this stage says it out loud rather than leaving the cell empty.

    Three sources, in order:

    1. **The bank's own wording**, for the 31 overhead rows. A commission or a charge is
       `OH - Bank Fees`, credit interest is `OH - Interest Income`. There is no project
       because the counterparty is the bank.
    2. **`PROJECT <name>`**, which the bank writes in the clear on 24 rows, looked up
       against the 586-row project report to recover its spelling: `AZURITE` is
       `Azurite Array`.
    3. **A code named in passing**, for the rows that mention the project without the
       keyword -- guarded, because some project codes are also counterparty names.

    Anything left is flagged, and flagged is a real answer here rather than a shrug.
    """
    narrative = row.raw.narrative_raw
    upper = narrative.upper()

    for phrases, value, reason in OVERHEAD_PHRASES:
        if any(phrase in upper for phrase in phrases):
            return Field(
                value=value,
                confidence=0.95,
                status="auto",
                evidence=Evidence(text=reason, source_list="Project Code Report"),
            )

    codes = [r["Project Code"] for r in lists.project_codes if r.get("Project Code")]

    named = _named_project(narrative)
    code = _lookup(named, codes)
    if code:
        start = upper.find(named)
        return Field(
            value=code,
            confidence=0.92,
            status="auto",
            evidence=Evidence(
                span=(start, start + len(named)) if start >= 0 else None,
                text=f"the bank text names project {named!r}",
                source_list="Project Code Report",
            ),
        )

    code = _project_named_anywhere(narrative, codes)
    if code:
        return Field(
            value=code,
            confidence=0.7,
            status="needs_review",
            evidence=Evidence(
                text=(
                    f"the bank text mentions {code!r}, but not as the project this was "
                    "booked against"
                ),
                source_list="Project Code Report",
            ),
        )

    if "INTERNAL TRANSFER" in upper and not (row.raw.credit or 0) > 0:
        return Field(
            value="OVERHEAD",
            confidence=0.6,
            status="needs_review",
            evidence=Evidence(
                text="an internal transfer out, which the working file books to overhead",
                source_list="Project Code Report",
            ),
        )

    return Field(
        value=NO_PROJECT,
        confidence=0.5,
        status="needs_review",
        evidence=Evidence(
            text="the bank text does not name a project, so somebody has to pick one",
            source_list="Project Code Report",
        ),
    )


# Reference lists that answer `classification` on their own, and how to say so to a fund
# manager. Measured on the ground truth at 6/6, 5/5 and 6/7.
DECISIVE_LIST = {
    "Deal & Position Master List": ("Investment", "the deal list"),
    "Investor Master List": ("Related Party", "the investor list"),
    "Vendor Master List": ("Vendor", "the vendor list"),
}

# What the bank writes when it says what a payment was for, in priority order, with the
# reason a reviewer reads. First phrase found wins, so the order is the rule: a fee line
# that also says CHARGE WAIVED is a fee, and `SHORT TERM LOAN:` is a loan between two
# funds rather than a loan into a holding company, so it has to be tested before `LOAN:`.
NARRATIVE_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("COMMISSION", "CHARGES FOR"), "Other", "the bank is charging its own fee here"),
    (("CREDIT INTEREST",), "Other", "this is interest the bank paid on the account"),
    (
        ("INTERNAL TRANSFER", "INTERNAL FX TRANSFER"),
        "Internal",
        "the bank text calls this an internal transfer",
    ),
    (
        ("PMT FRM",),
        "Investment Transfer",
        "the bank text describes a payment from one fund to another",
    ),
    (
        ("SHORT TERM LOAN", "SHORT-TERM LOAN"),
        "Investment Transfer",
        "the bank text describes a short-term loan between two funds",
    ),
    (
        ("EQUITY:", "LOAN:", "PAYMENT FROM"),
        "Investment",
        "the bank text describes money going into an investment",
    ),
    (
        ("CHARGE WAIVED",),
        "Internal",
        "the bank waived its charge, which it does on the fund's own transfers",
    ),
]


def _first_phrase(
    narrative: str, rules: list[tuple[tuple[str, ...], str, str]]
) -> tuple[str, str, str] | None:
    """The first rule phrase present in the narrative, with what it means.

    Searched against the raw text rather than the normalised form, so the phrase that
    decided the answer can be highlighted on the exact characters the reviewer sees.
    """
    haystack = narrative.upper()
    for phrases, value, reason in rules:
        for phrase in phrases:
            if phrase in haystack:
                return phrase, value, reason
    return None


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

    The other 82 rows -- matched in `Related Party Master`, or matched nowhere at all --
    split four ways each, and there the bank's own words decide: `NARRATIVE_RULES` reads
    what the text says the payment was for. A related party with nothing in the text
    saying why keeps `Related Party` as a proposal for a reviewer.

    Together that is 93 of 100. The three it gets wrong are the three the human marked
    `Review`, which is their own way of saying they could not tell either; there is no
    signal in those rows that separates them from the ones next to them. Four rows fall
    through to a reviewer with no value at all. Returning the majority value `Other`
    would have scored 32 more and misrepresented a guess as an answer, which is the
    failure this whole product argues against.
    """
    matched = row.fields.get("matched_sender_beneficiary")
    source = matched.evidence.source_list if matched and matched.value else ""

    if source in DECISIVE_LIST:
        value, where = DECISIVE_LIST[source]
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

    narrative = row.raw.narrative_raw
    found = _first_phrase(narrative, NARRATIVE_RULES)
    if found:
        phrase, value, reason = found
        start = narrative.upper().index(phrase)
        return Field(
            value=value,
            confidence=0.85,
            status="auto",
            evidence=Evidence(
                span=(start, start + len(phrase)),
                text=reason,
                source_list="Narrative",
            ),
        )

    if source == "Related Party Master":
        # A related party with nothing in the text saying what the payment was for. The
        # counterparty is the only evidence there is, so it is the proposal -- but a
        # proposal made on that little goes to a reviewer rather than straight through.
        return Field(
            value="Related Party",
            confidence=0.5,
            status="needs_review",
            evidence=Evidence(
                span=matched.evidence.span,
                text=(
                    f"{matched.value!r} is a related party, but the bank text does not "
                    "say what the payment was for"
                ),
                source_list="Related Party Master",
            ),
            alternatives=[
                Alternative(value="Internal", confidence=0.2),
                Alternative(value="Investment Transfer", confidence=0.2),
            ],
        )

    return Field(
        value=None,
        confidence=0.0,
        status="needs_review",
        evidence=Evidence(
            text=(
                "we could not tell who this was to or from, and the bank text does not "
                "say what kind of payment it is"
            ),
            source_list="Narrative",
        ),
    )


def resolved_position(row: Row, lists: ReferenceLists) -> Field:
    """Stage 5. Position under the deal, from a 6,637-row master. Investments only --
    filled on 30 of 100 rows."""
    raise NotImplementedError("W2")


def pulled_out_project_code(row: Row, lists: ReferenceLists) -> Field:
    """Stage 3. The project word as the bank wrote it, before any lookup.

    Filled on 25 of 100 rows, and kept separate from the code it resolves to for the same
    reason the sender/beneficiary pair is split: extraction and matching fail differently,
    and a reviewer looking at a wrong code needs to see whether the bank was misread or
    the master list was.
    """
    named = _named_project(row.raw.narrative_raw)
    if not named:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(
                text="the bank text does not name a project", source_list="Narrative"
            ),
        )
    start = row.raw.narrative_raw.upper().find(named)
    return Field(
        value=named,
        confidence=0.9,
        status="auto",
        evidence=Evidence(
            span=(start, start + len(named)) if start >= 0 else None,
            text="read from the bank text",
            source_list="Narrative",
        ),
    )


# What the counterpart line books to, given what kind of transaction it is and which way
# the money went: (money in, money out). `Investment` is not in here because equity and
# loan both go out, and the bank text is what separates them -- see the stage.
#
# This is the whole column, near enough. Measured against the ground truth with the
# human's own classification substituted in, the table is right on 98 of 100 rows, which
# says the account is a consequence of the classification rather than a separate question.
COUNTERPART_ACCOUNTS: dict[str, tuple[str, str]] = {
    "Other": ("Income - Bank Interest", "Expense - Bank Charges"),
    "Internal": ("Currency Correcting Credit", "Currency Correcting Debit"),
    "Investment Transfer": ("Receivable", "Payable - Third Party"),
    "Related Party": ("Receivable - Related Party", "Payable - Related Party"),
    "Vendor": ("Accounts Payable", "Accounts Payable"),
    "Review": ("Suspense (credit)", "Suspense (debit)"),
}

# How to describe each kind to a reviewer, so the reason reads as a sentence.
KIND_PHRASES = {
    "Other": "this is the bank charging a fee or paying interest",
    "Internal": "this is a transfer between the fund's own accounts",
    "Investment Transfer": "this is a transfer between two funds",
    "Related Party": "this is a payment with a related party",
    "Vendor": "this is a payment to a supplier",
    "Review": "this row was flagged for review",
}


def counterparty_transtype(row: Row, lists: ReferenceLists) -> Field:
    """Stage 4. The account the counterpart line books to.

    Filled on all 100 rows, across twelve different accounts. It looks like the hardest
    column on the sheet and it is very nearly the easiest, because it is not an
    independent question: once you know what kind of transaction this is and which way
    the money went, the account follows. A transfer between two funds is a `Receivable`
    when the money came in and a `Payable - Third Party` when it went out.

    So this stage reads `classification` rather than the narrative, and inherits its
    doubt: the Process sheet's own instruction is that each value is only as good as the
    stage before it, so a classification that went to a reviewer sends this there too.

    Two accounts do not fall out of the table:

    * `Investment` splits into equity and loan, and both go out. The bank says which.
    * `Suspense` is not an answer, it is the Process sheet parking a row for somebody to
      investigate -- so those rows go to a reviewer however confident the table is.
    """
    decided = row.fields.get("classification")
    kind = decided.value if decided else None
    if not kind:
        return Field(
            value=None,
            confidence=0.0,
            status="needs_review",
            evidence=Evidence(
                text=(
                    "we could not say what kind of transaction this is, so we cannot say "
                    "what account the other side belongs in"
                ),
                source_list="Process sheet, stage 4",
            ),
        )

    incoming = (row.raw.credit or 0) > 0
    narrative = row.raw.narrative_raw.upper()
    alternative: str | None = None

    if kind == "Investment":
        equity = "EQUITY:" in narrative
        value = "Investments - Equity - Purchase" if equity else "Investments - Loan - Purchase"
        alternative = "Investments - Loan - Purchase" if equity else "Investments - Equity - Purchase"
        reason = (
            "the bank text calls this equity"
            if equity
            else "the bank text describes a loan rather than equity"
        )
    elif kind == "Internal" and not incoming and "INTERNAL TRANSFER" in narrative:
        # The Process sheet parks a plain internal transfer out rather than booking it.
        value = "Suspense (debit)"
        alternative = "Currency Correcting Debit"
        reason = (
            "the bank calls this an internal transfer but does not say what it was for, "
            "so it is parked for somebody to investigate"
        )
    elif kind in COUNTERPART_ACCOUNTS:
        pair = COUNTERPART_ACCOUNTS[kind]
        value, alternative = (pair[0], pair[1]) if incoming else (pair[1], pair[0])
        reason = (
            f"{KIND_PHRASES[kind]}, and the money "
            f"{'came in' if incoming else 'went out'}"
        )
    else:
        return Field(
            value=None,
            confidence=0.0,
            status="needs_review",
            evidence=Evidence(
                text=f"we have no rule for booking a {kind!r} transaction",
                source_list="Process sheet, stage 4",
            ),
        )

    parked = value.startswith("Suspense")
    inherited = decided.status != "auto"
    if parked or inherited:
        status, confidence = "needs_review", 0.5
    else:
        status, confidence = "auto", 0.9
    if inherited and not parked:
        reason += ", but that depends on the type of transaction, which is not settled yet"

    return Field(
        value=value,
        confidence=confidence,
        status=status,
        evidence=Evidence(
            span=decided.evidence.span,
            text=reason,
            source_list="Process sheet, stage 4",
        ),
        alternatives=[Alternative(value=alternative, confidence=0.3)] if alternative else [],
    )


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
