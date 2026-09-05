"""Process a workspace: statements and reference lists in, reviewable rows out.

This is the whole interface for running the product. Before it existed the pipeline
existed twice -- the CLI ran it as two commands, the upload route ran it as a third copy
with function-local imports to dodge an import cycle -- and a caller had to know eight
ordered facts to assemble it, including that normalise mutates `row.raw` in place.

The two copies had already drifted: the upload path cleared reviewer decisions after a
run and the CLI did not. That divergence was invisible, and it mattered. Decisions are
keyed by `row_id`, which is positional, so a decision left over from a previous set of
statements re-attaches to whatever transaction is now in that position -- a reviewer's
approval silently transferred to a different payment. Invalidating them is a consequence
of running, not of running from the web, so it happens here.

Run:  python -m src.pipeline
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.checks import run as checks
from src.matcher import stages
from src.matcher.normalise import normalise
from src.matcher.reference import ReferenceLists
from src.matcher.run import apply_stages
from src.spine import workspace
from src.spine.build import load_workbook, parse_statements
from src.storage import db as store_db
from src.storage import store as data_store

OUT = Path("data")
ROWS = OUT / "rows.json"
DECISIONS = OUT / "decisions.json"
FLAGS = OUT / "flags.json"
FLAG_DECISIONS = OUT / "flag-decisions.json"

NO_DATA = (
    "No data to work from. Upload a reference workbook and at least one bank statement, "
    "or point YLOOKUP_DATA at the dataset directory."
)


@dataclass(frozen=True)
class PipelineResult:
    """What happened. Facts, not sentences -- the CLI prints them and the upload route
    words them differently, so neither formatting belongs in here."""

    rows: int
    sheets: int
    stages_total: int
    unwritten: list[str] = field(default_factory=list)
    failures: Counter = field(default_factory=Counter)
    checks_total: int = 0
    checks_applied: list[str] = field(default_factory=list)
    check_failures: Counter = field(default_factory=Counter)
    flags_found: int = 0

    @property
    def stages_applied(self) -> int:
        return self.stages_total - len(self.unwritten)

    @property
    def ok(self) -> bool:
        return not self.failures and not self.check_failures

    @property
    def flags(self) -> int:
        """Compatibility name for callers written before check execution was reported."""
        return self.flags_found


def run(space: workspace.Workspace | None = None) -> PipelineResult:
    """Read the workspace, match every row, persist the result.

    Ordering is this module's business: statements are normalised before matching because
    evidence spans index into the raw narrative, and reviewer decisions are dropped after
    a successful run because they no longer refer to these rows.

    Every workbook and statement this reads also goes into `src/storage/` -- one
    version-controlled record of everything ever uploaded, independent of the matcher's
    own `data/rows.json`. Re-running against unchanged files is a no-op there (content is
    compared by hash, not by when it arrived), so this costs nothing on the common case of
    re-running the same data twice. `src/checks/footing.py` runs here too, over the same
    rows before matching touches them, and its flags replace whatever was recorded on the
    previous run. The registered checks run through `src/checks/run.py`; their findings
    are mirrored into the unified store and their execution status is written to
    `data/flags.json`, so a clean run is distinguishable from one that never ran.
    """
    space = space or workspace.current()
    if not space.ready:
        raise SystemExit(NO_DATA)

    sheets = load_workbook(space.workbook)
    rows = parse_statements(space.statements)
    check_result = checks.apply_checks(rows)
    conn = store_db.connect()
    try:
        data_store.ingest_workbook(conn, space.workbook)
        for statement_path in space.statement_files:
            data_store.ingest_pdf(conn, statement_path)
        data_store.record_flags(conn, check_result.flags)
    finally:
        conn.close()

    for row in rows:
        row.raw.narrative_normalised, _ = normalise(row.raw.narrative_raw)

    payload, unwritten, failures = apply_stages(
        [row.to_dict() for row in rows], ReferenceLists.from_workbook(sheets)
    )

    OUT.mkdir(parents=True, exist_ok=True)
    ROWS.write_text(json.dumps(payload, indent=2))
    FLAGS.write_text(
        json.dumps(
            {
                "checks_total": check_result.checks_total,
                "checks_applied": check_result.checks_applied,
                "check_failures": dict(check_result.failures),
                "flags_found": len(check_result.flags),
                "flags": [asdict(flag) for flag in check_result.flags],
            },
            indent=2,
        )
    )
    DECISIONS.unlink(missing_ok=True)
    FLAG_DECISIONS.unlink(missing_ok=True)

    return PipelineResult(
        rows=len(payload),
        sheets=len(sheets),
        stages_total=len(stages.REGISTRY),
        unwritten=unwritten,
        failures=failures,
        checks_total=check_result.checks_total,
        checks_applied=check_result.checks_applied,
        check_failures=check_result.failures,
        flags_found=len(check_result.flags),
    )


def main() -> int:
    result = run()
    print(
        f"{result.rows} transactions from {result.sheets} sheets · "
        f"{result.stages_applied}/{result.stages_total} stages applied"
    )
    if result.unwritten:
        print("  not written yet: " + ", ".join(result.unwritten))
    for name, count in result.failures.items():
        print(f"  FAILED: {count} row(s) in {name} -- see the traceback above")
    print(
        f"{len(result.checks_applied)}/{result.checks_total} consistency checks applied · "
        f"{result.flags_found} finding(s)"
    )
    for name, count in result.check_failures.items():
        print(f"  CHECK FAILED: {name} ({count}) -- see the traceback above")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
