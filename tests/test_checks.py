"""The automated-check seam: success, stable findings, and isolated failures."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks.contract import Flag
from src.checks.run import apply_checks
from src.contract import Raw, Row


def a_row(row_id: int = 1) -> Row:
    return Row(
        row_id=row_id,
        source={"pdf": "statement.pdf", "page": 2},
        raw=Raw(account_number="ACC-1", credit=10.0, balance=20.0),
    )


def finding(rows: list[Row]) -> list[Flag]:
    row = rows[0]
    return [
        Flag(
            check="example",
            severity="error",
            message="the values do not reconcile",
            source={"pdf": row.source["pdf"], "page": 2, "row_id": row.row_id},
            expected=15.0,
            actual=20.0,
        )
    ]


def test_a_flag_id_is_stable_and_source_specific() -> None:
    first = finding([a_row(1)])[0]
    again = finding([a_row(1)])[0]
    another_row = finding([a_row(2)])[0]
    assert first.flag_id == again.flag_id
    assert first.flag_id != another_row.flag_id


def test_a_clean_check_is_recorded_as_applied() -> None:
    result = apply_checks([a_row()], [("clean", lambda rows: [])])
    assert result.checks_total == 1
    assert result.checks_applied == ["clean"]
    assert result.flags == [] and not result.failures


def test_a_broken_check_does_not_hide_other_results() -> None:
    def exploding(rows):
        raise ValueError("technical detail")

    result = apply_checks(
        [a_row()],
        [("broken", exploding), ("working", finding)],
    )
    assert result.checks_total == 2
    assert result.checks_applied == ["working"]
    assert len(result.flags) == 1
    assert sum(result.failures.values()) == 1


def test_a_malformed_check_result_is_isolated_too() -> None:
    result = apply_checks([a_row()], [("malformed", lambda rows: ["not a flag"])])
    assert result.checks_applied == [] and result.flags == []
    assert sum(result.failures.values()) == 1


def test_duplicate_findings_cannot_overwrite_each_other() -> None:
    result = apply_checks([a_row()], [("duplicating", lambda rows: finding(rows) + finding(rows))])
    ids = [flag.flag_id for flag in result.flags]
    assert len(ids) == 2 and len(set(ids)) == 2


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all automated check runner checks pass")
