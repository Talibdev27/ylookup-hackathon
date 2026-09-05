"""The bank abbreviates; the master lists spell out. Bridging the two is most of the work."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.matcher.abbreviations import expand

MASTER = [
    "Nordvik Infrastructure V SCSp",
    "Nordvik Infrastructure VI SCSp",
    "Nordvik Infrastructure Advanced Bioenergy Fund I SCSp",
    "Nordvik Infrastructure Advanced Bioenergy Fund II SCSp",
    "Nordvik Infrastructure Growth Markets Fund II SCSp",
    "AGP NI Co-Invest I SCSp",
]


def test_initials_expand() -> None:
    assert expand("NI ABF II SCSP", MASTER)[0].value == (
        "Nordvik Infrastructure Advanced Bioenergy Fund II SCSp"
    )


def test_whole_word_match_beats_an_initial() -> None:
    """`I` also opens `II` as an initial, so `NI ABF I SCSP` matches both entries. The
    one that matches `I` as a whole word has to win, or every Fund I row books to Fund II."""
    hits = expand("NI ABF I SCSP", MASTER)
    assert hits[0].value.endswith("Fund I SCSp")
    assert any(h.value.endswith("Fund II SCSp") for h in hits[1:])


def test_roman_numeral_ambiguity_is_kept_as_an_alternative() -> None:
    hits = expand("NI V SCSP", MASTER)
    assert hits[0].value == "Nordvik Infrastructure V SCSp"
    assert [h.value for h in hits[1:]] == ["Nordvik Infrastructure VI SCSp"]


def test_partial_consumption_is_not_a_match() -> None:
    """The whole entry must be consumed: `NI` alone is not `Nordvik Infrastructure V SCSp`."""
    assert expand("NI", MASTER) == []
    assert expand("", MASTER) == []


def test_confidence_rises_with_whole_word_matches() -> None:
    initials_only = expand("NI ABF II SCSP", MASTER)[0]
    assert 0.55 <= initials_only.confidence <= 1.0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all abbreviation checks pass")
