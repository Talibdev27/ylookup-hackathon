"""The front door band.

It has to stand on its own before there is a video, and absorb one later without the
page changing shape around it -- that is the whole reason the link is conditional.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader

from src.ui import labels

ENV = Environment(loader=FileSystemLoader("src/ui/templates"), autoescape=True)
ENV.globals.update(
    label=labels.label, question=labels.question, money=labels.money,
    direction=labels.direction, pretty_date=labels.pretty_date,
    certainty=labels.certainty, statement_label=labels.statement_label,
    highlight=labels.highlight, check_label=labels.check_label,
    severity_label=labels.severity_label,
)


def render(**kw) -> str:
    base = dict(
        queue=[], unattached_flags=[], show_all=False, total=0,
        summary={}, checks={}, space=None, suggestions=[],
        has_data=True, export={}, flagged=23, video_url=None,
    )
    base.update(kw)
    return ENV.get_template("review.html").render(**base)


def test_it_says_what_the_tool_is_without_a_video() -> None:
    html = render(video_url=None)
    assert "journal entries out" in html
    assert "52 of" in html and "100 counterparties" in html
    assert "Watch the demo" not in html


def test_the_finding_is_counted_not_hardcoded() -> None:
    assert ">23<" in render(flagged=23)
    assert ">7<" in render(flagged=7)


def test_no_finding_block_when_nothing_is_flagged() -> None:
    """A client's own statements may contradict nothing. Saying '0 rows where their own
    rule is contradicted' would be a boast about finding nothing."""
    html = render(flagged=0, video_url=None)
    assert "contradicts the file they shipped" not in html
    assert "journal entries out" in html


def test_singular_when_exactly_one_row_is_flagged() -> None:
    assert "row where" in render(flagged=1) and "rows where" not in render(flagged=1)


def test_the_video_link_appears_once_there_is_one() -> None:
    html = render(video_url="https://youtu.be/abc123")
    assert "https://youtu.be/abc123" in html
    assert "Watch the demo" in html
    assert 'rel="noopener"' in html


def test_the_band_is_hidden_before_any_statements_are_loaded() -> None:
    """An empty deployment should say 'load your statements', not pitch itself."""
    assert "journal entries out" not in render(has_data=False)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all intro checks pass")
