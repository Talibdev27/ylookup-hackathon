"""Where the data for a run lives.

Until now every path pointed at one folder on one laptop. A fund manager cannot use
that, so a run reads from a *workspace*: a directory holding one reference workbook and
a set of statements.

    data/workspace/
        reference.xlsx      the master lists -- uploaded once, changes rarely
        statements/*.pdf    this week's statements -- uploaded every week

The bundled hackathon dataset is just the workspace you get when nothing is uploaded
yet, so the demo works from a clean checkout and real use works the same way.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path("data/workspace")
BUNDLED = Path(
    os.environ.get("YLOOKUP_DATA", str(Path.home() / "Downloads" / "Ylookup Hackathon Datasets"))
) / "01-bank-statements-to-journal-entries"


@dataclass
class Workspace:
    workbook: Path | None
    statements: Path | None

    @property
    def ready(self) -> bool:
        return bool(self.workbook and self.statements and self.statement_files)

    @property
    def statement_files(self) -> list[Path]:
        return sorted(self.statements.glob("*.pdf")) if self.statements else []

    @property
    def is_bundled(self) -> bool:
        """True when the *reference workbook* is the bundled sample.

        Deliberately separate from `uses_bundled_statements`: uploading this week's
        statements against reference lists that are already set up is the normal case, so
        the two halves of a workspace are bundled or not independently.
        """
        return self.workbook is not None and BUNDLED in self.workbook.parents

    @property
    def uses_bundled_statements(self) -> bool:
        return self.statements is not None and self.statements.resolve() == (
            BUNDLED / "statements"
        ).resolve()


def _uploaded() -> Workspace:
    workbook = WORKSPACE / "reference.xlsx"
    statements = WORKSPACE / "statements"
    return Workspace(
        workbook=workbook if workbook.exists() else None,
        statements=statements if statements.is_dir() else None,
    )


def _bundled() -> Workspace:
    workbooks = sorted((BUNDLED / "workbook").glob("*.xlsx")) if BUNDLED.is_dir() else []
    statements = BUNDLED / "statements"
    return Workspace(
        workbook=workbooks[0] if workbooks else None,
        statements=statements if statements.is_dir() else None,
    )


def current() -> Workspace:
    """What this run should read. Uploaded data wins; the bundled dataset is the fallback.

    A half-finished upload -- statements but no workbook -- falls back rather than
    failing, so the app is never left in a state where nothing works.
    """
    uploaded = _uploaded()
    if uploaded.ready:
        return uploaded
    bundled = _bundled()
    if uploaded.statements and uploaded.statement_files and bundled.workbook:
        # Statements uploaded against reference data that is already set up.
        return Workspace(workbook=bundled.workbook, statements=uploaded.statements)
    return bundled


def save_workbook(source: Path) -> Path:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    target = WORKSPACE / "reference.xlsx"
    shutil.copyfile(source, target)
    return target


def clear_statements() -> Path:
    target = WORKSPACE / "statements"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    return target
