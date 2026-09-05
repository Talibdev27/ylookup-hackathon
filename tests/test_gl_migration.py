"""Dataset 02 (investor-level GL -> loader): real-data checks.

Counts asserted here are what the code actually finds when run against the real
workbooks, verified by hand before being written down -- not copied from the README in
`02-investor-level-gl-to-loader/README.md`, which states 4/16/198 for the same three
gaps. They currently match the README exactly (see `analyze.py`'s docstrings for the
verification), but if the source data ever drifts, this file's numbers are the ones to
trust and update -- that is this repo's own stated philosophy (trust the data over any
prior documentation).

Run:  python -m pytest tests/test_gl_migration.py -q      (or: python tests/test_gl_migration.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checks.contract import Flag
from src.gl_migration import analyze, load

# Loaded once at module scope -- the GL sheet alone takes several seconds to parse, and
# every test below needs the same data.
GL = load.load_source_gl()
SHEETS = load.load_output_workbook()
UPLOAD = SHEETS[load.UPLOAD_SHEET]


def test_missing_legal_entities_matches_verified_count() -> None:
    """52 distinct legal entities in the upload template, 77 in Entity Listing, 4 in the
    template but not the listing. Matches the README's stated 4 exactly."""
    flags = analyze.check_missing_legal_entities(UPLOAD, SHEETS[load.ENTITY_LISTING_SHEET])
    assert len(flags) == 4, f"expected 4 legal entities missing from Entity Listing, got {len(flags)}"
    assert all(isinstance(f, Flag) for f in flags)
    assert all(f.check == "gl_migration.legal_entity_not_listed" for f in flags)
    assert all(f.severity == "info" for f in flags)
    assert len({f.flag_id for f in flags}) == 4  # each entity gets its own stable id


def test_missing_deals_matches_verified_count() -> None:
    """41 distinct deal names in the upload template, 41 in Deals List, 16 in the
    template but not the listing. Matches the README's stated 16 exactly."""
    flags = analyze.check_missing_deals(UPLOAD, SHEETS[load.DEALS_LIST_SHEET])
    assert len(flags) == 16, f"expected 16 deals missing from Deals List, got {len(flags)}"
    assert all(f.check == "gl_migration.deal_not_listed" for f in flags)


def test_missing_investors_matches_verified_count() -> None:
    """543 distinct investor names in Investor Mapping, 348 in Investors List, 198 in the
    mapping but not the listing. Matches the README's stated 198 exactly -- the largest
    flag set of the four, which is the real finding, not a bug."""
    flags = analyze.check_missing_investors(
        SHEETS[load.INVESTOR_MAPPING_SHEET], SHEETS[load.INVESTORS_LIST_SHEET]
    )
    assert len(flags) == 198, f"expected 198 investors missing from Investors List, got {len(flags)}"
    assert all(f.check == "gl_migration.investor_not_listed" for f in flags)


def test_mapping_gaps_surfaces_every_administered_row() -> None:
    """The Mapping Gaps sheet has 2 rows in the real workbook -- both already documented,
    administrator-reviewed gaps. One Flag per row, no more, no fewer."""
    flags = analyze.check_mapping_gaps(SHEETS[load.MAPPING_GAPS_SHEET])
    assert len(flags) == 2, f"expected 2 mapping-gap rows, got {len(flags)}"
    assert all(f.check == "gl_migration.mapping_gap" for f in flags)
    assert all(f.severity == "review" for f in flags)


def test_entity_totals_tie_between_gl_and_upload_template() -> None:
    """The real finding: grouped by Legal Entity (52 entities common to both files, out
    of 79 in the source GL -- the other 27 are simply not in this tranche), every single
    entity's total ties to the cent between the source GL's signed `Amount (Local
    Currency)` and the upload template's `Investor Amount (Local)` x `Is Debit` sign.
    Verified row-by-row for one entity (Chalbury Co-Invest L.P.: 1,522 rows on each side,
    both summing to 0.00) before trusting this aggregate. If this ever produces a flag,
    something in the migration has actually broken -- investigate before assuming the
    check is wrong."""
    flags = analyze.check_entity_totals_tie(GL, UPLOAD)
    assert flags == [], f"expected every entity to tie, got {len(flags)} mismatches: {flags[:3]}"


def test_analyze_returns_every_flag_type() -> None:
    """The combined entry point: 4 + 16 + 198 + 2 + 0 = 220 flags in total against the
    real data, spanning four distinct check names (the tie check contributes none, since
    it is clean)."""
    flags = analyze.analyze()
    assert len(flags) == 4 + 16 + 198 + 2
    checks_seen = {f.check for f in flags}
    assert checks_seen == {
        "gl_migration.legal_entity_not_listed",
        "gl_migration.deal_not_listed",
        "gl_migration.investor_not_listed",
        "gl_migration.mapping_gap",
    }
    ids = [f.flag_id for f in flags]
    assert len(ids) == len(set(ids)), "every flag should have a distinct, stable id"


if __name__ == "__main__":
    test_missing_legal_entities_matches_verified_count()
    test_missing_deals_matches_verified_count()
    test_missing_investors_matches_verified_count()
    test_mapping_gaps_surfaces_every_administered_row()
    test_entity_totals_tie_between_gl_and_upload_template()
    test_analyze_returns_every_flag_type()
    print("all gl_migration checks pass")
