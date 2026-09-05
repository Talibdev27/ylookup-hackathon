"""Load the sheets dataset 02's checks need, from both workbooks, into plain
lists-of-dicts. Loading only -- `analyze.py` does the checking, the same split
`src/spine/build.py` keeps from `src/checks/`.

Both workbooks here are much larger than dataset 1's reference workbook: the GL sheet
alone is ~34,000 rows across 43 columns. Measured on this machine, `openpyxl` in
`read_only` mode takes ~16s to walk every row of that sheet; `src/spine/xlsx.py`'s
dependency-free reader does the same in ~5s (it was written for exactly this reason --
see its own docstring). This module uses `xlsx.py`'s `Workbook` throughout rather than
switching readers per sheet, so one code path is verified against both file sizes.

No `YLOOKUP_DATA` env var for this dataset. The paths below are hardcoded relative to
`DATA_ROOT`, which defaults to the hackathon data folder as it sits next to this repo
on disk. Override `DATA_ROOT` (or pass an explicit `path=` to any loader) if the dataset
moves or a caller wants to point at a copy.
"""
from __future__ import annotations

from pathlib import Path

from src.spine.xlsx import Workbook

# src/gl_migration/load.py -> src/gl_migration -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

# The dataset lives one level above this repo, in the shared hackathon data folder.
DATA_ROOT = REPO_ROOT.parent / "Ylookup Hackathon Datasets" / "02-investor-level-gl-to-loader"

SOURCE_GL = (
    DATA_ROOT / "source" / "Investor-Level GL - Q2 activity - all entities (anonymised).xlsx"
)
OUTPUT_LOADER = (
    DATA_ROOT / "output" / "Tranche 1 - reference and verified loader v4c (anonymised).xlsx"
)

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
