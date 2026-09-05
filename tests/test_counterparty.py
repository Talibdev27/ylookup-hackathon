"""Extracting the counterparty from bank text, and matching it to a reference list."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.matcher.counterparty import (
    complete, drop_address, extract, fold, locate, match, tidy,
)

NARRATIVE = (
    "NI ABF II MIZARCO S.A R., PAYMENT FROM NORDVIK INFRASTRUCTURE ABF II SCSP, "
    "TO TO NI ABF II MIZARCO S.A R.L. PROJECT BOREAS"
)


def test_fold_bridges_the_two_spellings() -> None:
    """The bank writes uppercase ASCII, the master list writes accents and punctuation.
    Without folding, these never compare equal and nothing matches at all."""
    assert fold("NI ABF II MizarCo S.à r.l.") == fold("NI ABF II MIZARCO S.A R.L.")


def test_extract_takes_the_first_name_fragment() -> None:
    fragment, span = extract(NARRATIVE)
    # The stop closing `S.A R.` is part of the name, not punctuation around it, so it
    # survives -- the human transcribing these keeps whichever form the bank wrote.
    assert fragment == "NI ABF II MIZARCO S.A R."
    # The span is what gets highlighted on screen, so it must be the text on the page.
    assert NARRATIVE[span[0] : span[1]] == fragment


def test_extract_skips_reference_fragments() -> None:
    """Account numbers and transaction ids come first on some statements."""
    fragment, _ = extract("52443473437109-3528152584, TRENTBECK AUDIT LUXEMBOURG")
    assert fragment == "TRENTBECK AUDIT LUXEMBOURG"


def test_tidy_strips_the_line_number_prefix() -> None:
    assert tidy("1/NORDVIK INFRASTRUCTURE PARTNER") == "NORDVIK INFRASTRUCTURE PARTNER"


def test_complete_reads_a_full_spelling_out_of_the_middle_of_a_fragment() -> None:
    """The bank cut this name at a line break and spelled it out later, mid-fragment,
    where no fragment scan can see it. Reading from the later mention to the end of the
    name recovers it.

    An unguarded word window was measured at 17/55 and 7/55 against 37/55 for whole
    fragments only, which is why the two guards matter: a completion stops at the bank's
    own instruction words, and has to add name rather than punctuation."""
    assert complete("NI ABF II MIZARCO S.A R.", NARRATIVE) == "NI ABF II MIZARCO S.A R.L."
    # When the fuller form is its own fragment, it is picked up.
    assert complete("TRENTBECK AUDIT", "TRENTBECK AUDIT, TRENTBECK AUDIT LUXEMBOURG") == (
        "TRENTBECK AUDIT LUXEMBOURG"
    )


def test_completion_must_add_name_not_punctuation() -> None:
    """The same counterparty is written `... U.A` in one place and `... U.A.` in another.
    Neither is more complete, so a later mention that folds identically is not a
    completion and the fragment the bank led with stands."""
    narrative = "NI GMF II COOPERATIEF U.A, 93301QH142TF, NI GMF II COOPERATIEF U.A. PROJECT IAPETUS."
    assert complete("NI GMF II COOPERATIEF U.A", narrative) == "NI GMF II COOPERATIEF U.A"


def test_completion_stops_where_the_name_stops() -> None:
    """The bank runs a name straight into why it paid, with no punctuation between."""
    narrative = "NI RANFJORD II SCSP, 25515MS49ERZ, TO NI RANFJORD II SCSP (EUR). PROJECT, RANFJORD II."
    assert complete("NI RANFJORD II SCSP", narrative) == "NI RANFJORD II SCSP"


def test_a_street_address_is_not_part_of_the_company_name() -> None:
    """`COVBURY ENERGI A/S FENNSTEAD 41` is a company and an address run together. The
    name closes at its legal form; the house number is what marks the rest as an address,
    because `NI ABF II MIZARCO S.A R.L.` also continues past one."""
    assert drop_address("COVBURY ENERGI A/S FENNSTEAD 41") == "COVBURY ENERGI A/S"
    assert drop_address("NI ABF II MIZARCO S.A R.L.") == "NI ABF II MIZARCO S.A R.L."


def test_a_name_is_read_back_off_the_page_with_its_line_wrap() -> None:
    """A name read off a whitespace-collapsed copy has lost the comma the bank wrapped
    into it. Both the value and the highlighted span have to be the page's own text."""
    narrative = "SHORT TERM LOAN: FROM NORDVIK, INFRASTRUCTURE V SCSP TO NORDVIK, INFRASTRUCTURE V CN SCSP."
    text, span = locate("NORDVIK INFRASTRUCTURE V CN SCSP", narrative)
    assert text == "NORDVIK, INFRASTRUCTURE V CN SCSP"
    assert narrative[span[0] : span[1]] == text


def test_currency_decides_between_two_spellings_of_one_counterparty() -> None:
    """`NI GMF II Coöperatief U.A.` and `... - USD` are the same counterparty held in two
    currencies. The narrative never says which; the row's currency does."""
    lists = [
        ("Related Party Master", ["NI GMF II Coöperatief U.A."]),
        ("Deal & Position Master List", ["NI GMF II Coöperatief U.A. - USD"]),
    ]
    assert match("NI GMF II COOPERATIEF U.A", lists, currency="USD")[0].value.endswith("- USD")


def test_no_match_returns_nothing_rather_than_a_guess() -> None:
    assert match("SOMEBODY NOT ON ANY LIST", [("Vendor Master List", ["Trentbeck Audit - Lu"])]) == []
    assert extract("") is None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all counterparty checks pass")
