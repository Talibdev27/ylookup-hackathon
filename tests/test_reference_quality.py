"""Legal Entity Master List near-duplicate detection, checked both ways: what the real
97-row list actually contains, and that the check catches something when it should.

Run:  python -m pytest tests/ -q      (or: python tests/test_reference_quality.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks import reference_quality
from src.spine.build import load_workbook


def test_real_legal_entity_list() -> None:
    """The bundled 97-row Legal Entity Master List has zero exact-fold collisions (no
    row is the same name typed two different ways) and exactly 11 token-superset
    candidates at the 0.9 overlap threshold -- every one of which, on manual review
    (see the module docstring), differs from its partner by exactly one meaningful
    fund-structuring qualifier (Non-US/US, an Elimination leg, Blocked), not a typo.
    If this count ever changes, check whether the master list itself changed before
    touching the check."""
    sheets = load_workbook()
    names = [r["Legal Entity"] for r in sheets["Legal Entity Master List"] if r.get("Legal Entity")]
    assert len(names) == 97

    flags = reference_quality.check(names)
    exact = [f for f in flags if f.check == "legal_entity_exact_fold_duplicate"]
    near = [f for f in flags if f.check == "legal_entity_near_duplicate"]

    assert exact == [], f"expected zero exact-fold duplicates, got {exact}"
    assert len(near) == 11, f"expected 11 near-duplicate candidates, got {len(near)}: {near}"
    assert all(f.severity == "review" for f in near)
    assert all(f.actual >= reference_quality.OVERLAP_THRESHOLD for f in near)


def test_catches_an_exact_fold_duplicate() -> None:
    """Same entity, typed two different ways -- accents/punctuation/case are exactly
    what `fold()` normalises away, so these collide."""
    names = [
        "NI ABF II MizarCo S.à r.l.",
        "NI ABF II MIZARCO S A R L",
        "Some Other Fund SCSp",
    ]
    flags = reference_quality.check(names)
    exact = [f for f in flags if f.check == "legal_entity_exact_fold_duplicate"]
    assert len(exact) == 1
    assert exact[0].severity == "error"
    assert set(exact[0].actual) == {"NI ABF II MizarCo S.à r.l.", "NI ABF II MIZARCO S A R L"}


def test_catches_a_high_overlap_token_superset() -> None:
    """One entry is a strict superset of the other's tokens, with only a single extra
    word out of many -- exactly the "typed the suffix inconsistently" case the
    superset/overlap rule exists for."""
    long_name = "Nordvik Infrastructure Advanced Bioenergy Fund Two Holdco SCSp Feeder Vehicle"
    short_name = "Nordvik Infrastructure Advanced Bioenergy Fund Two Holdco SCSp Feeder"
    names = [long_name, short_name, "Completely Unrelated Entity Ltd"]
    flags = reference_quality.check(names)
    near = [f for f in flags if f.check == "legal_entity_near_duplicate"]
    assert len(near) == 1
    assert near[0].severity == "review"
    assert near[0].source == {"shorter": short_name, "longer": long_name}


def test_ignores_genuinely_unrelated_names() -> None:
    """Short, unrelated names should never be flagged just because one happens to be a
    literal substring/token-subset of a much longer, unrelated one below the overlap bar."""
    names = ["NI Fund Alpha SCSp", "NI Fund Alpha Beta Gamma Delta Epsilon Zeta SCSp"]
    flags = reference_quality.check(names)
    assert flags == []


if __name__ == "__main__":
    test_real_legal_entity_list()
    test_catches_an_exact_fold_duplicate()
    test_catches_a_high_overlap_token_superset()
    test_ignores_genuinely_unrelated_names()
    print("all reference_quality checks pass")
