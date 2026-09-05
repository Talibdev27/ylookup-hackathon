"""The review screen renders text that came out of a PDF. Escaping is not optional."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui.labels import (
    check_label,
    flag_action_label,
    highlight,
    is_long_value,
    money,
    pretty_date,
    severity_label,
    statement_label,
    value_preview,
)


def test_statement_label_is_readable() -> None:
    label = statement_label("20260331_NI_V_SCSP_CALDER_EUR_030041.pdf", 2)
    assert "NI V SCSP" in label
    assert "EUR" in label
    assert "31 Mar 2026" in label
    assert "page 2" in label
    # An unparseable name falls back to itself rather than raising in a template.
    assert statement_label("odd.pdf") == "odd.pdf"


def test_money_drops_the_sign() -> None:
    """Direction is carried by wording. A minus sign in front of a number is easy to
    misread and easy to miss entirely."""
    assert money(-301908.7, "EUR") == "€301,908.70"
    assert money(301908.7, "EUR") == "€301,908.70"
    assert money(None, "EUR") == ""


def test_highlight_marks_the_span() -> None:
    assert str(highlight("NI ABF I SCSP, PMT FRM", [(0, 13)])) == (
        "<mark>NI ABF I SCSP</mark>, PMT FRM"
    )


def test_highlight_merges_overlapping_spans() -> None:
    assert str(highlight("ABCDEFGH", [(0, 4), (2, 6)])) == "<mark>ABCDEF</mark>GH"


def test_highlight_escapes_the_narrative() -> None:
    """The text comes from a PDF, so it is not trusted to be markup-safe."""
    rendered = str(highlight("<script>alert(1)</script> PAYMENT", [(26, 33)]))
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "<mark>PAYMENT</mark>" in rendered


def test_highlight_without_spans_is_plain_escaped_text() -> None:
    assert str(highlight("a & b", [None])) == "a &amp; b"


def test_pretty_date() -> None:
    assert pretty_date("2026-03-31") == "31 Mar 2026"
    assert pretty_date(None) == ""


def test_check_vocabulary_is_for_a_reviewer() -> None:
    assert check_label("balance_continuity") == "Balance continuity"
    assert severity_label("error") == "Does not reconcile"
    assert flag_action_label("false_positive") == "Marked as not an issue"


def test_long_values_are_previewed_without_changing_the_original() -> None:
    value = "Position " + "x" * 300
    assert is_long_value(value)
    assert len(value_preview(value)) < len(value)
    assert value_preview(value).endswith("…")
    assert not is_long_value("short")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all label checks pass")
