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
    assert result.stages_applied == 4, "six stages are declared unwritten"
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
