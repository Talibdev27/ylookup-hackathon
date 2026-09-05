"""Extracting the counterparty from bank text, and matching it to a reference list."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.matcher.counterparty import complete, extract, fold, match, tidy

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
    assert fragment == "NI ABF II MIZARCO S.A R."
    assert NARRATIVE[span[0] : span[1]] == fragment, "span must index the raw narrative"


def test_extract_skips_reference_fragments() -> None:
    """Account numbers and transaction ids come first on some statements."""
    fragment, _ = extract("52443473437109-3528152584, TRENTBECK AUDIT LUXEMBOURG")
    assert fragment == "TRENTBECK AUDIT LUXEMBOURG"


def test_tidy_strips_the_line_number_prefix() -> None:
    assert tidy("1/NORDVIK INFRASTRUCTURE PARTNER") == "NORDVIK INFRASTRUCTURE PARTNER"


def test_complete_recovers_a_truncated_name() -> None:
    assert complete("NI ABF II MIZARCO S.A R.", NARRATIVE) == "NI ABF II MIZARCO S.A R.L."


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
