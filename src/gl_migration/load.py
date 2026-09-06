"""Load the sheets dataset 02's checks need, from both workbooks, into plain
lists-of-dicts. Loading only -- `analyze.py` does the checking, the same split
`src/spine/build.py` keeps from `src/checks/`.

Both workbooks here are much larger than dataset 1's reference workbook: the GL sheet
alone is ~34,000 rows across 43 columns. Measured on this machine, `openpyxl` in
`read_only` mode takes ~16s to walk every row of that sheet; `src/spine/xlsx.py`'s
dependency-free reader does the same in ~5s (it was written for exactly this reason --
see its own docstring). This module uses `xlsx.py`'s `Workbook` throughout rather than
switching readers per sheet, so one code path is verified against both file sizes.

`DATA_ROOT` resolves the same way the rest of the repo does: `YLOOKUP_DATA` if it is
set, then the folder beside this repo, then `~/Downloads` -- the first of those that
actually exists. It used to be the repo-sibling path alone, which is where the data sits
on one machine and nowhere else, so `./run-tests.sh` died here for everybody else,
including anyone who cloned the repo and followed the README.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.spine.xlsx import Workbook

# src/gl_migration/load.py -> src/gl_migration -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

_DATASET = "02-investor-level-gl-to-loader"


def _resolve_data_root() -> Path:
    """Where dataset 02 lives, agreeing with `src/spine/workspace.py` on the answer.

    Returns the first candidate that exists, and the last one unchanged if none do, so
    a missing dataset surfaces as a readable path in the error rather than as a silent
    fallback to somewhere the data was never going to be.
    """
    candidates = []
    env = os.environ.get("YLOOKUP_DATA")
    if env:
        candidates.append(Path(env))
    candidates.append(REPO_ROOT.parent / "Ylookup Hackathon Datasets")
    candidates.append(Path.home() / "Downloads" / "Ylookup Hackathon Datasets")
    for base in candidates:
        if (base / _DATASET).is_dir():
            return base / _DATASET
    return candidates[-1] / _DATASET


DATA_ROOT = _resolve_data_root()


SOURCE_GL = (
    DATA_ROOT / "source" / "Investor-Level GL - Q2 activity - all entities (anonymised).xlsx"
)
OUTPUT_LOADER = (
    DATA_ROOT / "output" / "Tranche 1 - reference and verified loader v4c (anonymised).xlsx"
)


def available() -> bool:
    """Whether dataset 02 is actually on this machine.

    It is not bundled with the repo -- a clone without it is the normal case for anybody
    but us -- so callers and tests skip on this rather than crashing the suite."""
    return SOURCE_GL.is_file() and OUTPUT_LOADER.is_file()

GL_SHEET = "Investor-Level GL"
UPLOAD_SHEET = "Upload Template (VERIFIED v4c)"
ENTITY_LISTING_SHEET = "Entity Listing"
DEALS_LIST_SHEET = "Deals List"
INVESTORS_LIST_SHEET = "Investors List"
LE_MAPPING_SHEET = "LE Mapping"
INVESTOR_MAPPING_SHEET = "Investor Mapping"
DEAL_MAPPING_SHEET = "Deal Mapping"
COA_MAPPING_SHEET = "CoA Mapping"
MAPPING_GAPS_SHEET = "Mapping Gaps"

# Every output-workbook sheet analyze.py touches. Loaded together, off one Workbook
# instance, so the zip is only opened and its shared-strings table only built once.
OUTPUT_SHEETS = [
    UPLOAD_SHEET,
    ENTITY_LISTING_SHEET,
    DEALS_LIST_SHEET,
    INVESTORS_LIST_SHEET,
    LE_MAPPING_SHEET,
    INVESTOR_MAPPING_SHEET,
    DEAL_MAPPING_SHEET,
    COA_MAPPING_SHEET,
    MAPPING_GAPS_SHEET,
]


def load_source_gl(path: Path | str = SOURCE_GL) -> list[dict[str, str]]:
    """The quarter's investor-level GL: one row per journal transaction line, ~34,000
    rows. `Amount (Local Currency)` is signed (positive = debit, negative = credit) --
    verified against `Debits (Local Currency) - Credits (Local Currency)` by hand before
    being relied on in `analyze.py`'s tie check."""
    return Workbook(str(path)).records(GL_SHEET)


def load_output_workbook(path: Path | str = OUTPUT_LOADER) -> dict[str, list[dict[str, str]]]:
    """Every sheet `analyze.py` needs from the reference/verified loader workbook, keyed
    by sheet name exactly as in `OUTPUT_SHEETS`."""
    book = Workbook(str(path))
    return {name: book.records(name) for name in OUTPUT_SHEETS}
