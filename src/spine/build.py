"""Build the data spine: statements + workbook -> data/spine.sqlite and data/rows.json.

Run:  python -m src.spine.build
Must complete in under a minute from a clean checkout. Everything downstream reads the
outputs of this module and never opens an .xlsx or a PDF again.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from src.contract import Row
from src.matcher.normalise import normalise
from src.spine import pdf, workspace
from src.spine.xlsx import Workbook

OUT = Path("data")


def _paths() -> tuple[Path, Path]:
    space = workspace.current()
    if not space.ready:
        raise SystemExit(
            "No data to work from. Upload a reference workbook and at least one bank "
            "statement, or point YLOOKUP_DATA at the dataset directory."
        )
    return space.workbook, space.statements


WORKBOOK, STATEMENTS = (lambda s: (s.workbook, s.statements))(workspace.current())

# Row counts verified against the bundled workbook. If a sheet does not match, the loader
# is broken -- fail loudly rather than let a silent truncation reach the matcher.
#
# These are only checked for the bundled dataset. Somebody else's reference workbook has
# their own row counts, and asserting ours against theirs would reject every real upload.
# Note 'DIU ' has a trailing space in the workbook. That is not a typo here.
# The lists the matcher cannot work without. Everything else in the workbook is optional.
REQUIRED_SHEETS = [
    "Related Party Master",
    "Legal Entity Master List",
    "Investor Master List",
    "Vendor Master List",
    "Deal & Position Master List",
]

EXPECTED_ROWS = {
    "Staging Sheet": 100,
    "DIU ": 200,
    "Deal & Position Master List": 6635,
    "Investor Master List": 637,
    "CoA": 558,
    "Project Code Report": 587,
    "Related Party Master": 297,
    "Vendor Master List": 246,
    "Bank Account Report": 245,
    "Vendor Codes": 196,
    "Legal Entity Master List": 97,
    "Korean and Taiwanese": 32,
    "Allocation Rule": 26,
    "Process": 15,
    "Account Map": 7,
}


def load_workbook(path: Path | None = None) -> dict[str, list[dict[str, str]]]:
    space = workspace.current()
    path = path or space.workbook
    if path is None:
        raise SystemExit("No reference workbook. Upload one, or set YLOOKUP_DATA.")
    book = Workbook(str(path))
    sheets = {name: book.records(name) for name in book.sheet_names()}
    if space.is_bundled and Path(path) == space.workbook:
        for sheet, expected in EXPECTED_ROWS.items():
            actual = len(sheets.get(sheet, []))
            if actual != expected:
                raise AssertionError(f"{sheet!r}: expected {expected} data rows, loaded {actual}")
    missing = [s for s in REQUIRED_SHEETS if s not in sheets]
    if missing:
        raise SystemExit(
            "This workbook is missing the reference lists the matcher needs: "
            + ", ".join(missing)
        )
    return sheets


def write_sqlite(sheets: dict[str, list[dict[str, str]]], out: Path = OUT / "spine.sqlite") -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    conn = sqlite3.connect(out)
    for sheet, records in sheets.items():
        if not records:
            continue
        table = "".join(ch if ch.isalnum() else "_" for ch in sheet.strip().lower()).strip("_")
        columns = list(records[0])
        safe = [f'"{c}"' for c in columns]
        conn.execute(f'CREATE TABLE "{table}" ({", ".join(f"{c} TEXT" for c in safe)})')
        conn.executemany(
            f'INSERT INTO "{table}" VALUES ({", ".join("?" * len(columns))})',
            [[r.get(c, "") for c in columns] for r in records],
        )
    conn.commit()
    conn.close()


def parse_statements(directory: Path | None = None) -> list[Row]:
    """One Row per transaction line across every statement in the directory.

    The bundled dataset is checked against its known 100 rows; an upload is not, because
    nobody else's week has 100 transactions in it.
    """
    space = workspace.current()
    directory = directory or space.statements
    rows = pdf.parse_statements(directory)
    # The 100-row check belongs to the bundled *statements*, not the bundled workbook.
    # Gating it on the workbook rejected every upload made against reference lists that
    # were already set up -- which is the normal way this gets used.
    is_sample = directory.resolve() == (workspace.BUNDLED / "statements").resolve()
    if is_sample and len(rows) != 100:
        raise AssertionError(f"parsed {len(rows)} transactions from the sample data, expected 100")
    if not rows:
        raise SystemExit(f"No transactions found in {directory}. Are these bank statements?")
    return rows


def main() -> int:
    space = workspace.current()
    if not space.ready:
        raise SystemExit(
            "No data to work from. Upload a reference workbook and at least one bank "
            "statement, or point YLOOKUP_DATA at the dataset directory."
        )
    sheets = load_workbook(space.workbook)
    write_sqlite(sheets)
    rows = parse_statements(space.statements)
    for row in rows:
        row.raw.narrative_normalised, _ = normalise(row.raw.narrative_raw)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.json").write_text(json.dumps([r.to_dict() for r in rows], indent=2))
    print(f"spine built: {len(sheets)} sheets, {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
