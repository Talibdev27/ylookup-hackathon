"""Running the whole thing.

There was no test at this level before, for the same reason there was no module: with the
pipeline assembled inline by each caller, a test would have had to assemble it a fourth
way. One interface means the test crosses the same seam the CLI and the upload route do.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import pipeline
from src.spine import workspace


def test_running_the_sample_workspace() -> None:
    result = pipeline.run(workspace.current())

    assert result.rows == 100
    assert result.sheets == 15
    assert result.stages_total == 10
    assert result.stages_applied == 5, "five stages are declared unwritten"
    assert result.ok, f"stages failed: {dict(result.failures)}"

    rows = json.loads(pipeline.ROWS.read_text())
    assert len(rows) == 100
    assert rows[0]["raw"]["narrative_normalised"], "normalise runs before matching"


def test_a_run_invalidates_reviewer_decisions() -> None:
    """The divergence that made this module worth building.

    The upload route cleared decisions after a run and the CLI did not. Decisions are
    keyed by `row_id`, which is positional, so a leftover decision re-attaches to whatever
    transaction is now in that position -- a reviewer's approval silently transferred to a
    different payment. It is a consequence of running, so the pipeline owns it and both
    callers get it.
    """
    pipeline.DECISIONS.write_text(json.dumps({"17": {"choice": "approve", "value": "stale"}}))
    assert pipeline.DECISIONS.exists()

    pipeline.run(workspace.current())

    assert not pipeline.DECISIONS.exists(), "decisions from a previous run must not survive"


def test_an_empty_workspace_says_so_rather_than_crashing() -> None:
    empty = workspace.Workspace(workbook=None, statements=None)
    assert not empty.ready
    try:
        pipeline.run(empty)
    except SystemExit as stop:
        assert "Upload a reference workbook" in str(stop)
    else:
        raise AssertionError("an empty workspace should stop with an explanation")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all pipeline checks pass")


def test_a_row_can_answer_more_than_one_question() -> None:
    """21 of the rows in the queue ask two questions. Decisions were first keyed by row
    alone, so answering the second silently overwrote the answer to the first."""
    from src.ui import app

    app.DECISIONS.unlink(missing_ok=True)
    client = app.app.test_client()

    for field, choice, value in [
        ("matched_sender_beneficiary", "manual", "NIP P/S"),
        ("cash_leg_transtype", "approve", "Cash - Disbursed - EUR"),
    ]:
        response = client.post(
            "/rows/1/decide", json={"choice": choice, "field": field, "value": value}
        )
        assert response.status_code == 200, response.get_json()

    answered = app.load_decisions()["1"]
    assert answered["matched_sender_beneficiary"]["value"] == "NIP P/S"
    assert answered["cash_leg_transtype"]["choice"] == "approve"
    app.DECISIONS.unlink(missing_ok=True)


def test_a_correction_needs_a_value_but_giving_up_does_not() -> None:
    """"I can't tell either" is a real answer -- without it the row never leaves the
    queue. An empty typed correction is not."""
    from src.ui import app

    app.DECISIONS.unlink(missing_ok=True)
    client = app.app.test_client()

    blank = client.post("/rows/2/decide", json={"choice": "manual", "field": "x", "value": "   "})
    assert blank.status_code == 400

    gave_up = client.post("/rows/2/decide", json={"choice": "unresolved", "field": "x"})
    assert gave_up.status_code == 200
    assert app.load_decisions()["2"]["x"]["choice"] == "unresolved"

    unnamed = client.post("/rows/2/decide", json={"choice": "approve", "value": "y"})
    assert unnamed.status_code == 400, "a decision must say which field it answers"
    app.DECISIONS.unlink(missing_ok=True)
