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
from src.spine import pdf
from src.spine.xlsx import Workbook

DATASET = Path(
    os.environ.get("YLOOKUP_DATA", str(Path.home() / "Downloads" / "Ylookup Hackathon Datasets"))
)
BANK = DATASET / "01-bank-statements-to-journal-entries"
WORKBOOK = BANK / "workbook" / "Bank statement to journal entries - working file (anonymised).xlsx"
STATEMENTS = BANK / "statements"
OUT = Path("data")

# Row counts verified against the real workbook. If a sheet does not match, the loader
# is broken -- fail loudly rather than let a silent truncation reach the matcher.
# Note 'DIU ' has a trailing space in the workbook. That is not a typo here.
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


def load_workbook(path: Path = WORKBOOK) -> dict[str, list[dict[str, str]]]:
    book = Workbook(str(path))
    sheets = {name: book.records(name) for name in book.sheet_names()}
    for sheet, expected in EXPECTED_ROWS.items():
        actual = len(sheets.get(sheet, []))
        if actual != expected:
            raise AssertionError(f"{sheet!r}: expected {expected} data rows, loaded {actual}")
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


def parse_statements(directory: Path = STATEMENTS) -> list[Row]:
    """Seven PDFs, four currencies. Verified to yield exactly 100 transactions."""
    rows = pdf.parse_statements(directory)
    if len(rows) != EXPECTED_ROWS["Staging Sheet"]:
        raise AssertionError(f"parsed {len(rows)} transactions, expected 100")
    return rows


def main() -> int:
    sheets = load_workbook()
    write_sqlite(sheets)
    rows = parse_statements()
    for row in rows:
        row.raw.narrative_normalised, _ = normalise(row.raw.narrative_raw)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.json").write_text(json.dumps([r.to_dict() for r in rows], indent=2))
    print(f"spine built: {len(sheets)} sheets, {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
