"""Checks for dataset 02: the investor-level GL -> loader migration.

The migration's own README (`02-investor-level-gl-to-loader/README.md`, in the hackathon
data folder) names four known gaps, preserved from the original and explicitly "do not
treat as errors": legal entities, deal names and investor names that appear on one side
of a crosswalk but not the other, plus a `Mapping Gaps` sheet the administrator already
populated with unmapped GL accounts. Every count below was re-derived from the actual
workbooks rather than copied from the README -- see `tests/test_gl_migration.py` for the
verification and the docstring on each check for what was actually found.

The one new check here, `check_entity_totals_tie`, was not in the README at all. The
question it answers: after applying the entity/deal/investor mapping, does the money
still add up between the source GL and the upload template? Grouping by Legal Entity is
the right join key -- verified by hand (see its docstring) rather than assumed, the same
way `src/reports/statements.py`'s `ties()` was verified against the bundled sample before
being written down.
"""
from __future__ import annotations

from src.checks.contract import Flag
from src.gl_migration import load

TOLERANCE = 0.01  # cents of floating-point noise, not a real discrepancy


def _clean(value: object) -> str:
    return str(value or "").strip()


def check_missing_legal_entities(
    upload: list[dict[str, str]], entity_listing: list[dict[str, str]]
) -> list[Flag]:
    """One flag per legal entity that appears in the upload template but not in Entity
    Listing. Verified against the real workbooks: 52 distinct legal entities in the
    upload template, 77 in Entity Listing, 4 in the template but not the listing --
    matches the README's stated 4 exactly."""
    listed = {_clean(row.get("Entity")) for row in entity_listing if _clean(row.get("Entity"))}
    upload_entities = sorted(
        {_clean(row.get("Legal Entity")) for row in upload if _clean(row.get("Legal Entity"))}
    )
    flags = []
    for entity in upload_entities:
        if entity in listed:
            continue
        flags.append(
            Flag(
                check="gl_migration.legal_entity_not_listed",
                severity="info",
                message=(
                    f"Legal entity {entity!r} appears in the upload template but not in "
                    "Entity Listing. Preserved from the original migration -- a known gap, "
                    "not a new error."
                ),
                source={
                    "workbook": "output",
                    "sheet": load.UPLOAD_SHEET,
                    "legal_entity": entity,
                },
                expected="present in Entity Listing",
                actual="absent",
            )
        )
    return flags


def check_missing_deals(upload: list[dict[str, str]], deals_list: list[dict[str, str]]) -> list[Flag]:
    """One flag per deal name that appears in the upload template but not in Deals List.
    Verified against the real workbooks: 41 distinct deal names in the upload template,
    41 in Deals List, 16 in the template but not the listing -- matches the README's
    stated 16 exactly."""
    listed = {_clean(row.get("Deal Name")) for row in deals_list if _clean(row.get("Deal Name"))}
    upload_deals = sorted(
        {_clean(row.get("Deal Name")) for row in upload if _clean(row.get("Deal Name"))}
    )
    flags = []
    for deal in upload_deals:
        if deal in listed:
            continue
        flags.append(
            Flag(
                check="gl_migration.deal_not_listed",
                severity="info",
                message=(
                    f"Deal {deal!r} appears in the upload template but not in Deals List. "
                    "Preserved from the original migration -- a known gap, not a new error."
                ),
                source={"workbook": "output", "sheet": load.UPLOAD_SHEET, "deal_name": deal},
                expected="present in Deals List",
                actual="absent",
            )
        )
    return flags


def check_missing_investors(
    investor_mapping: list[dict[str, str]], investors_list: list[dict[str, str]]
) -> list[Flag]:
    """One flag per investor name that appears in Investor Mapping but not in Investors
    List. Verified against the real workbooks: 543 distinct investor names in Investor
    Mapping, 348 in Investors List, 198 in the mapping but not the listing -- matches the
    README's stated 198 exactly. This is the largest flag set by far; that is the real
    finding, not a bug in the check."""
    listed = {_clean(row.get("Investor")) for row in investors_list if _clean(row.get("Investor"))}
    mapped_investors = sorted(
        {
            _clean(row.get("Investor Name"))
            for row in investor_mapping
            if _clean(row.get("Investor Name"))
        }
    )
    flags = []
    for investor in mapped_investors:
        if investor in listed:
            continue
        flags.append(
            Flag(
                check="gl_migration.investor_not_listed",
                severity="info",
                message=(
                    f"Investor {investor!r} appears in Investor Mapping but not in "
                    "Investors List. Preserved from the original migration -- a known "
                    "gap, not a new error."
                ),
                source={
                    "workbook": "output",
                    "sheet": load.INVESTOR_MAPPING_SHEET,
                    "investor": investor,
                },
                expected="present in Investors List",
                actual="absent",
            )
        )
    return flags


def check_mapping_gaps(mapping_gaps: list[dict[str, str]]) -> list[Flag]:
    """One flag per row already present in the `Mapping Gaps` sheet -- the administrator
    populated this on purpose with GL account / transaction type combinations that had no
    mapping to the target chart of accounts and were sent back for a decision. Surfacing
    a row that already exists in the workbook as a Flag is legitimate: it is real,
    documented data, not something invented here. 2 rows found in the real workbook."""
    flags = []
    for i, row in enumerate(mapping_gaps):
        flags.append(
            Flag(
                check="gl_migration.mapping_gap",
                severity="review",
                message=(
                    f"GL account {row.get('GL Account')!r} / trans type "
                    f"{row.get('Trans Type')!r} has no mapping to the target chart of "
                    f"accounts ({row.get('Row Count')} source rows, "
                    f"{row.get('Total Amount (Entity Currency)')} total local-currency "
                    "amount). Sent back to the administrator for a decision -- not "
                    "resolved by this migration."
                ),
                source={
                    "workbook": "output",
                    "sheet": load.MAPPING_GAPS_SHEET,
                    "row_index": i,
                },
                expected=None,
                actual=dict(row),
            )
        )
    return flags


def check_entity_totals_tie(
    gl: list[dict[str, str]], upload: list[dict[str, str]]
) -> list[Flag]:
    """Does the total amount tie between the source GL and the upload template, once
    grouped by Legal Entity?

    Legal Entity is the join key: every legal entity in the upload template (52 of them)
    also appears in the source GL, which additionally covers 27 other entities not yet in
    scope for this tranche -- so the comparison is restricted to entities present on both
    sides, not all 79 in the source.

    Amount sign conventions differ between the two files and were verified by hand, not
    assumed, before writing this check:
    - GL: `Amount (Local Currency)` is already signed -- positive for a debit, negative
      for a credit. Confirmed against `Debits (Local Currency) - Credits (Local
      Currency)` for every row in a 2,000-row sample: zero mismatches.
    - Upload template: `Investor Amount (Local)` is unsigned; direction comes from the
      separate `Is Debit` column ('Y'/'N').

    Verified end to end for one entity by hand (Chalbury Co-Invest L.P.): 1,522 GL rows
    and 1,522 upload-template rows, both summing to 0.00, with the very first row on each
    side showing the identical 1,557,610.43 amount. Run across all 52 common entities,
    every single one ties to the cent -- zero mismatches. This function still emits a
    Flag per mismatching entity so the check means something if that ever stops being
    true (e.g. a future tranche introduces a real discrepancy)."""
    gl_totals: dict[str, float] = {}
    for row in gl:
        entity = _clean(row.get("Legal Entity"))
        if not entity:
            continue
        try:
            amount = float(row.get("Amount (Local Currency)") or 0)
        except ValueError:
            continue
        gl_totals[entity] = gl_totals.get(entity, 0.0) + amount

    upload_totals: dict[str, float] = {}
    for row in upload:
        entity = _clean(row.get("Legal Entity"))
        if not entity:
            continue
        try:
            amount = float(row.get("Investor Amount (Local)") or 0)
        except ValueError:
            continue
        sign = 1.0 if _clean(row.get("Is Debit")).upper() == "Y" else -1.0
        upload_totals[entity] = upload_totals.get(entity, 0.0) + sign * amount

    flags = []
    for entity in sorted(set(gl_totals) & set(upload_totals)):
        gl_total = round(gl_totals[entity], 2)
        upload_total = round(upload_totals[entity], 2)
        if abs(gl_total - upload_total) <= TOLERANCE:
            continue
        flags.append(
            Flag(
                check="gl_migration.entity_totals_do_not_tie",
                severity="error",
                message=(
                    f"Legal entity {entity!r}: source GL sums to {gl_total:,.2f} but the "
                    f"upload template sums to {upload_total:,.2f} (local currency), a "
                    f"difference of {gl_total - upload_total:,.2f}."
                ),
                source={"workbook": "both", "legal_entity": entity},
                expected=gl_total,
                actual=upload_total,
            )
        )
    return flags


def analyze(
    gl_path: object = load.SOURCE_GL,
    output_path: object = load.OUTPUT_LOADER,
) -> list[Flag]:
    """Run every dataset-02 check and return the combined list of Flags."""
    gl = load.load_source_gl(gl_path)
    sheets = load.load_output_workbook(output_path)
    upload = sheets[load.UPLOAD_SHEET]

    flags: list[Flag] = []
    flags += check_missing_legal_entities(upload, sheets[load.ENTITY_LISTING_SHEET])
    flags += check_missing_deals(upload, sheets[load.DEALS_LIST_SHEET])
    flags += check_missing_investors(
        sheets[load.INVESTOR_MAPPING_SHEET], sheets[load.INVESTORS_LIST_SHEET]
    )
    flags += check_mapping_gaps(sheets[load.MAPPING_GAPS_SHEET])
    flags += check_entity_totals_tie(gl, upload)
    return flags
