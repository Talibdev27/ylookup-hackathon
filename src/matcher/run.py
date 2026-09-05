"""Apply the matcher stages to data/rows.json, in place.

Every stage has the same shape, `(row, lists) -> Field`, and they run in the order
declared by `stages.REGISTRY`. Adding a stage means writing a function and adding a line,
both in `stages.py`.

Three outcomes, kept apart on purpose:

  applied            the stage produced a field
  not written yet    the stage raised NotImplementedError, which is a declaration
  failed             the stage raised something else, which is a defect

The previous version could not tell the second from the third. It caught TypeError
alongside NotImplementedError to detect stages whose arguments it had guessed wrong, so a
genuine TypeError inside a working stage was reported as "not implemented yet" and the
column silently scored 0/100. Uniform arity removed the need to guess, and the
distinction is now real.

Called by src/pipeline.py, which owns the ordering and the persistence.
"""
from __future__ import annotations

import traceback
from collections import Counter
from dataclasses import asdict

from src.contract import Evidence, Field, Raw, Row
from src.matcher import stages
from src.matcher.reference import ReferenceLists
from src.spine.build import load_workbook

def load_lists() -> ReferenceLists:
    return ReferenceLists.from_workbook(load_workbook())


def _failed(stage_name: str, error: Exception) -> Field:
    """What a reviewer sees when a stage breaks on their row.

    The row stays in the queue, because silently dropping a transaction out of a
    financial review is the exact failure this product argues against. The wording is
    plain English: the review screen renders `evidence.text` verbatim to a fund manager,
    and a traceback is the one thing that would break that. The technical detail goes to
    the console.
    """
    return Field(
        value=None,
        confidence=0.0,
        status="unresolved",
        evidence=Evidence(
            text="We hit a problem working this out, so it needs a person to look at it.",
            source_list=f"{stage_name} ({type(error).__name__})",
        ),
    )


def apply_stages(
    payload: list[dict], lists: ReferenceLists | None = None
) -> tuple[list[dict], list[str], Counter]:
    """Run every stage over every row. Returns the rows, the stages that are not written
    yet, and a count of per-stage failures."""
    lists = lists or ReferenceLists()
    unwritten: list[str] = []
    failures: Counter = Counter()

    for entry in payload:
        row = Row(row_id=entry["row_id"], source=entry["source"], raw=Raw(**entry["raw"]))
        for name, stage in stages.REGISTRY:
            if name in unwritten:
                continue
            try:
                result = stage(row, lists)
            except NotImplementedError:
                unwritten.append(name)
                continue
            except Exception as error:  # a defect in the stage, not a missing stage
                if not failures[name]:
                    traceback.print_exc()
                failures[name] += 1
                result = _failed(name, error)
            row.fields[name] = result
            entry.setdefault("fields", {})[name] = asdict(result)
    return payload, unwritten, failures
