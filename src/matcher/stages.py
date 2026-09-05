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
                value=lists.canonical_spelling(loose.value),
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
#
# The comma is allowed after the keyword because the bank wraps lines mid-phrase and puts
# one at the wrap point, so `PROJECT, RANFJORD II.` is one phrase broken across two lines
# rather than a project called nothing followed by a separate fragment.
PROJECT_NAMED = re.compile(r"PROJECT[:,\s]+([A-Z0-9][A-Z0-9\- ]*)")

# Overhead codes the bank's own wording settles, before any lookup happens. These are 31
# of the 100 rows and none of them names a project, because there is no project: the
# counterparty is the bank itself.
OVERHEAD_PHRASES = [
    (("CREDIT INTEREST",), "OH - Interest Income", "this is interest the bank paid"),
    (("COMMISSION", "CHARGES FOR"), "OH - Bank Fees", "this is a fee the bank charged"),
]

NO_PROJECT = "Flag for review - no project match"

# Money the fund moves to fund its own running costs rather than a project. All nine rows
# in the sample that book to `OVERHEAD` say one of these, and no row saying one of these
# books anywhere else. Direction does not matter: the same transfer is an outgoing on one
# statement and an incoming on the other, and both legs are overhead.
OVERHEAD_MOVEMENTS: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("COVER INVOICES",),
        "OVERHEAD",
        "the money was moved to pay the fund's own invoices, not a project's",
    ),
    (
        ("INTERNAL TRANSFER", "INTERNAL FX TRANSFER"),
        "OVERHEAD",
        "an internal transfer, which the working file books to overhead rather than to a project",
    ),
]


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


def _project_named_anywhere(
    narrative: str, codes: list[str], lists: ReferenceLists | None = None
) -> str | None:
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

    # A project mentioned in passing belongs to whoever the money moved with. On a row
    # where that is a company none of the lists knows, there is nobody to attach the
    # project to, and the mention is as likely to be the deal it settles as the project it
    # books to -- so the row is flagged rather than assigned one.
    if found and lists is not None:
        words = found[0].split()
        unknown = not counterparty.match(found[0], lists.counterparty_lists())
        if unknown and any(counterparty._looks_like_legal_form(word) for word in words):
            return None

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

    code = _project_named_anywhere(narrative, codes, lists)
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

    overhead = _first_phrase(narrative, OVERHEAD_MOVEMENTS)
    if overhead:
        phrase, value, reason = overhead
        start = upper.index(phrase)
        return Field(
            value=value,
            confidence=0.85,
            status="auto",
            evidence=Evidence(
                span=(start, start + len(phrase)),
                text=reason,
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
]

# Tested after the counterparty has had its say, not before. A waived charge is a fact
# about the bank's fee, not about the payment: the bank waives it on the fund's own
# transfers, and also on payments to a related party, so on its own it separates nothing.
# Above the related party check it turned five payments to `NIP P/S` into `Internal`.
FEE_WAIVER_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("CHARGE WAIVED",),
        "Internal",
        "the bank waived its charge, which it does on transfers between the fund's own accounts",
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


def _classify_an_unknown_name(
    name: str, lists: ReferenceLists, pulled: Field
) -> Field | None:
    """What can still be said about a counterparty none of the lists names.

    Two things, and only for a name that reads like an organisation -- the fee lines the
    bank writes against itself (`COMMISSION EUR 6`, `CHARGES FOR 2`) reach here too, and
    neither of these applies to them.

    A name opening with the group's own domain code belongs to the group, whether or not
    that particular entity has been added to a sheet yet. Otherwise a name carrying a
    legal form is a real company that the reference data does not know, and nothing about
    the payment can be settled from a company nobody can identify -- so it is flagged,
    using the client's own word for that.
    """
    words = name.split()
    domain = lists.domain_code
    if domain and words and words[0].upper() == domain.upper():
        return Field(
            value="Related Party",
            confidence=0.7,
            status="needs_review",
            evidence=Evidence(
                span=pulled.evidence.span,
                text=(
                    f"{name!r} is one of the group's own entities, but it is not on the "
                    "related party list"
                ),
                source_list="Related Party Master",
            ),
            alternatives=[Alternative(value="Other", confidence=0.2)],
        )

    if any(counterparty._looks_like_legal_form(word) for word in words):
        return Field(
            value="Review",
            confidence=0.6,
            status="needs_review",
            evidence=Evidence(
                span=pulled.evidence.span,
                text=(
                    f"{name!r} is a company, and it is on none of the reference lists, so "
                    "we cannot say what kind of transaction this is"
                ),
                source_list="Related Party, Legal Entity, Investor and Vendor lists",
            ),
        )
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
    unidentified = row.fields.get("pulled_out_sender_beneficiary")
    read_but_unknown = (
        unidentified.value if unidentified and unidentified.value and not source else ""
    )
    if read_but_unknown:
        settled = _classify_an_unknown_name(read_but_unknown, lists, unidentified)
        if settled:
            return settled

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

    own = _own_legal_entity(row)
    if matched and matched.value and own and counterparty.fold_legal_form(
        matched.value
    ) == counterparty.fold_legal_form(own):
        # The counterparty is this statement's own fund. Money that leaves an account and
        # arrives at the same legal entity has not left the fund, whichever list the name
        # was found on.
        return Field(
            value="Internal",
            confidence=0.9,
            status="auto",
            evidence=Evidence(
                span=matched.evidence.span,
                text=f"this is {own!r} moving money between its own accounts",
                source_list=source,
            ),
        )

    if source == "Related Party Master":
        # A related party with nothing in the text saying what the payment was for. The
        # counterparty is the only evidence there is, so it is the proposal -- but a
        # proposal made on that little goes to a reviewer rather than straight through.
        # Knowing who was paid outranks the fee-waiver flag, which is why that rule is
        # tested below this and not with the others.
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

    waived = _first_phrase(narrative, FEE_WAIVER_RULES)
    if waived:
        phrase, value, reason = waived
        start = narrative.upper().index(phrase)
        return Field(
            value=value,
            confidence=0.8,
            status="auto",
            evidence=Evidence(
                span=(start, start + len(phrase)), text=reason, source_list="Narrative"
            ),
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


def _security_kind(narrative: str) -> str | None:
    """Equity or funding loan, as the bank describes the purchase.

    `ACQ 100PER OF SHARES IN ...` buys equity. `PURCHAS 100PER OF LOAN PRINCIP` and
    `PURCHASE 100PER OF ACC INT` -- accrued interest -- are both the loan.
    """
    text = " ".join(narrative.upper().split())
    if "EQUITY:" in text or "SHARES" in text or "SHARE " in text:
        return "Equity"
    if "LOAN" in text or "PRINCIP" in text or "ACC INT" in text:
        return "Funding loan"
    return None


def resolved_position(row: Row, lists: ReferenceLists) -> Field:
    """Stage 5. Which position under the deal, from the same 6,635-row master.

    Reads the deal the stage before it settled, then narrows the master's rows three ways:
    the legal entity whose statement this is, whether the bank bought equity or loan, and
    the project named in the position text.

    That leaves exactly one position on 13 of the 30 rows. On 12 more it leaves two or
    four, and the answer is genuinely not in the bank text: `Cephalus Biogas 001 Limited -
    EUR (Halstead (Equity))` and `... (Equity)` are both real positions under the same
    deal, held by the same legal entity, for the same kind of security, and nothing in the
    narrative says Halstead. Those rows get every candidate under the human's own heading,
    `Review - multiple positions:`, which is what their working file says when the same
    thing happened to them.
    """
    deal = row.fields.get("resolved_deal")
    if not deal or not deal.value:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(
                text="there is no deal to find a position under",
                source_list="Deal & Position Master List",
            ),
        )

    wanted = set(deal.value.split(JOIN))
    candidates = [d for d in lists.deals if d.get("Deal Name") in wanted]

    entity = row.fields.get("matched_legal_entity")
    if entity and entity.value:
        mine = counterparty.fold_legal_form(entity.value)
        candidates = [
            d for d in candidates if counterparty.fold_legal_form(d.get("Legal Entity", "")) == mine
        ] or candidates

    kind = _security_kind(row.raw.narrative_raw)
    if kind:
        candidates = [
            d for d in candidates if d.get("Security Type", "").lower() == kind.lower()
        ] or candidates

    project = row.fields.get("matched_project_code")
    named = project.value if project and project.value else ""
    if named and not named.startswith(NOT_A_PROJECT):
        target = counterparty.fold(named)
        candidates = [
            d for d in candidates if f" {target} " in f" {counterparty.fold(d.get('Position', ''))} "
        ] or candidates

    positions = sorted({d["Position"] for d in candidates if d.get("Position")})
    if not positions:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(
                text=f"the deal master holds no position under {deal.value!r}",
                source_list="Deal & Position Master List",
            ),
        )
    if len(positions) > 1:
        return Field(
            value=MANY + JOIN.join(positions),
            confidence=0.4,
            status="needs_review",
            evidence=Evidence(
                text=(
                    f"{len(positions)} positions under this deal fit equally well, and the "
                    "bank text does not say which"
                ),
                source_list="Deal & Position Master List",
            ),
            alternatives=[Alternative(value=p, confidence=0.4) for p in positions[:4]],
        )
    return Field(
        value=positions[0],
        confidence=0.8,
        status="auto",
        evidence=Evidence(
            text="the only position under this deal that fits this payment",
            source_list="Deal & Position Master List",
        ),
    )


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


# Only an investment has a deal behind it. Measured on the ground truth: every one of the
# 30 rows carrying a deal is classified one of these two, and only one row classified this
# way carries no deal.
INVESTMENT_KINDS = {"Investment", "Investment Transfer"}

# The human's own wording when more than one row of the master fits. Reproduced rather
# than invented: it is what their working file says, and the review queue reads it.
MANY = "Review - multiple positions: "
JOIN = " | "

# Bookkeeping words that are not a project name.
NOT_A_PROJECT = ("Flag", "OH -", "OVERHEAD")


def _deals_named(name: str, currency: str, deal_names: list[str]) -> list[str]:
    """Deals whose name is this entity, preferring the one held in this row's currency."""
    if not name:
        return []
    target = counterparty.fold_legal_form(name)
    exact = [d for d in deal_names if counterparty.fold_legal_form(d) == target]
    if exact:
        return exact[:1]
    tagged = [d for d in deal_names if counterparty.fold_legal_form(d) == f"{target} {currency}"]
    if tagged:
        return tagged[:1]
    opened = sorted((d for d in deal_names if counterparty.fold_legal_form(d).startswith(target + " ")), key=len)
    return opened[:1]


def _deals_for_project(project: str, currency: str, lists: ReferenceLists) -> list[str]:
    """Every deal financing this project, preferring the ones held in this row's currency.

    More than one is a real answer here: a project financed through four holding vehicles
    has four deals, and the human joined them rather than picking one.

    The deal is not always named after the project. `Azurite Array` is financed through
    `NI V Azurite HoldCo Limited`, which does not carry the project's full name -- but the
    positions underneath it do, so the position text is searched when the deal names come
    back empty.
    """
    if not project or project.startswith(NOT_A_PROJECT):
        return []
    target = counterparty.fold(project)

    def in_currency(names: list[str]) -> list[str]:
        tagged = [d for d in names if counterparty.fold(d).endswith(f" {currency}")]
        return sorted(tagged or names)

    named = [d for d in lists.deal_names if f" {target} " in f" {counterparty.fold(d)} "]
    if named:
        return in_currency(named)
    held = {
        row["Deal Name"]
        for row in lists.deals
        if row.get("Deal Name")
        and f" {target} " in f" {counterparty.fold(row.get('Position', ''))} "
    }
    return in_currency(sorted(held))


def resolved_deal(row: Row, lists: ReferenceLists) -> Field:
    """Stage 5. The deal this transaction sits under, from the 6,635-row deal master.

    Filled on 30 of 100 rows, and the gate is what makes it tractable: every row the human
    gave a deal is one we classify `Investment` or `Investment Transfer`, and only one row
    we classify that way has no deal. Everything else -- a bank fee, an internal transfer,
    a supplier payment -- has no deal because there is no investment behind it, so this
    stage says nothing rather than reaching for the nearest name.

    Which name to look up depends on which kind it is, and the two are not interchangeable:

    * An `Investment` is money moving into a holding company, and that company is the deal.
      So the counterparty is the lookup.
    * An `Investment Transfer` is money moving between two of the fund's own vehicles to
      fund a project. The vehicles are not the deal; the project is.
    """
    kind = row.fields.get("classification")
    if not kind or kind.value not in INVESTMENT_KINDS:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(
                text="this is not an investment, so there is no deal behind it",
                source_list="Deal & Position Master List",
            ),
        )

    counterpart = row.fields.get("matched_sender_beneficiary")
    project = row.fields.get("matched_project_code")
    who = counterpart.value if counterpart else None
    what = project.value if project else None
    currency = row.raw.currency

    if kind.value == "Investment":
        # Without a counterparty there is nothing to look up: the project alone names the
        # deals of every vehicle financing it, which is a list rather than an answer.
        found = _deals_named(who, currency, lists.deal_names) if who else []
        reason = f"{who!r} is a deal in the master list" if found else ""
    else:
        found = _deals_for_project(what, currency, lists)
        reason = f"the money was moved to fund {what!r}" if found else ""
        if not found and who:
            found = _deals_named(who, currency, lists.deal_names)
            reason = f"{who!r} is a deal in the master list" if found else ""

    if not found:
        return Field(
            value=None,
            confidence=0.0,
            status="unresolved",
            evidence=Evidence(
                text="we could not tell which deal this belongs to",
                source_list="Deal & Position Master List",
            ),
        )
    if len(found) > 1:
        return Field(
            value=JOIN.join(found),
            confidence=0.5,
            status="needs_review",
            evidence=Evidence(
                text=(
                    f"{what!r} is financed through {len(found)} vehicles, so somebody has "
                    "to say which of them this payment belongs to"
                ),
                source_list="Deal & Position Master List",
            ),
            alternatives=[Alternative(value=d, confidence=0.5) for d in found[:4]],
        )
    return Field(
        value=found[0],
        confidence=0.85,
        status="auto",
        evidence=Evidence(text=reason, source_list="Deal & Position Master List"),
    )


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
