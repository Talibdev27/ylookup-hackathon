"""The spine is only useful if it agrees with the human ground truth.

These compare as multisets, not row-by-row: several statement rows share an identical
narrative, so a dict keyed on narrative silently collapses them and compares the wrong
pair. Counter intersection asks the question we actually mean -- does the same bag of
values come out of the PDFs as went into the human's staging sheet?

Run:  python -m pytest tests/ -q      (or: python tests/test_spine.py)
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.spine.build import STATEMENTS, load_workbook
from src.spine.pdf import parse_statements


def _norm(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _overlap(got: list[str], want: list[str]) -> int:
    return sum((Counter(got) & Counter(want)).values())


def test_statements_match_ground_truth() -> None:
    rows = parse_statements(STATEMENTS)
    truth = load_workbook()["Staging Sheet"]

    assert len(rows) == 100, f"parsed {len(rows)} transactions, expected 100"
    assert len(truth) == 100

    checks = {
        "narrative": ([_norm(r.raw.narrative_raw) for r in rows], [_norm(t["Narrative"]) for t in truth]),
        "bank_reference": ([_norm(r.raw.bank_reference) for r in rows], [_norm(t["Bank reference"]) for t in truth]),
        "currency": ([r.raw.currency for r in rows], [t["Currency"] for t in truth]),
        "account_number": ([r.raw.account_number for r in rows], [t["Account Number"] for t in truth]),
    }
    for name, (got, want) in checks.items():
        assert _overlap(got, want) == 100, f"{name}: only {_overlap(got, want)}/100 agree"


def test_separator_rows_are_not_glued_onto_references() -> None:
    """Day separators ("Balance brought forward ...") share the single-cell shape of a
    wrapped bank reference. Regression: they were being appended to the row above."""
    for row in parse_statements(STATEMENTS):
        assert "Balance" not in row.raw.bank_reference
        assert len(row.raw.bank_reference) <= 40


if __name__ == "__main__":
    test_statements_match_ground_truth()
    test_separator_rows_are_not_glued_onto_references()
    print("all spine checks pass")


def test_rows_align_to_ground_truth() -> None:
    """Regression: rows come out in statement-filename order, the staging sheet is in its
    own order, and only 11 of 100 line up by position. Scoring by index compares the
    wrong pairs and reports a plausible-looking wrong number, which is the worst kind."""
    import json

    from src.matcher.score import align

    rows = json.loads(open("data/rows.json").read())
    truth = load_workbook()["Staging Sheet"]
    assert len(align(rows, truth)) == 100


def test_alignment_key_is_unique() -> None:
    """An inter-fund transfer is written on both statements with the same narrative,
    amount and bank reference. Without the account number in the key, the two sides pair
    crosswise and three rows score against the wrong fund."""
    import json

    from src.matcher.score import _row_key, _truth_key

    rows = json.loads(open("data/rows.json").read())
    truth = load_workbook()["Staging Sheet"]
    assert len({_row_key(r) for r in rows}) == 100
    assert len({_truth_key(t) for t in truth}) == 100
