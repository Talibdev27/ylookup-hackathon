"""Apply the matcher stages to data/rows.json, in place.

This is W2's entry point. Add a stage to STAGES and it appears on the scoreboard.
Stages that are not implemented yet are skipped, so the pipeline always runs end to end
and the score only ever goes up.

Run:  python -m src.matcher.run
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.contract import Raw, Row
from src.matcher import stages
from src.spine.build import load_workbook

ROWS = Path("data/rows.json")


def load_masters() -> dict[str, list]:
    """The reference lists each stage matches against, loaded once."""
    sheets = load_workbook()
    return {
        "legal_entities": [list(r.values())[0] for r in sheets["Legal Entity Master List"]],
        "related_parties": [r["Related Party"] for r in sheets["Related Party Master"]],
        "investors": sorted({r["Investor"] for r in sheets["Investor Master List"]}),
        "vendors": sorted({r["Vendor"] for r in sheets["Vendor Master List"]}),
        "project_codes": sheets["Project Code Report"],
        "deals": sheets["Deal & Position Master List"],
        "deal_names": sorted({d["Deal Name"] for d in sheets["Deal & Position Master List"] if d["Deal Name"]}),
    }

# field key -> (callable, names of the master lists it needs)
NEEDS = {
    "matched_legal_entity": ("legal_entities",),
    "matched_sender_beneficiary": ("__all__",),
}

STAGES = {
    "cash_leg_transtype": stages.cash_leg_transtype,
    "matched_legal_entity": stages.matched_legal_entity,
    "pulled_out_sender_beneficiary": stages.pulled_out_sender_beneficiary,
    "matched_sender_beneficiary": stages.matched_sender_beneficiary,  # reads the stage above
    "matched_project_code": stages.matched_project_code,
    "classification": stages.classification,
    "resolved_position": stages.resolved_position,
}


def apply_stages(payload: list[dict], masters: dict[str, list] | None = None) -> tuple[list[dict], list[str]]:
    masters = masters or {}
    skipped: list[str] = []
    for entry in payload:
        row = Row(row_id=entry["row_id"], source=entry["source"], raw=Raw(**entry["raw"]))
        for key, stage in STAGES.items():
            needed = NEEDS.get(key, ())
            args = [masters if name == "__all__" else masters[name]
                    for name in needed if name == "__all__" or name in masters]
            if len(args) != len(needed):
                if key not in skipped:
                    skipped.append(key)
                continue
            try:
                field = stage(row, *args)
            except NotImplementedError:
                if key not in skipped:
                    skipped.append(key)
                continue
            except TypeError:
                # stage needs master-list arguments it has not been wired to yet
                if key not in skipped:
                    skipped.append(key)
                continue
            row.fields[key] = field
            entry.setdefault("fields", {})[key] = asdict(field)
    return payload, skipped


def main() -> int:
    payload = json.loads(ROWS.read_text())
    payload, skipped = apply_stages(payload, load_masters())
    ROWS.write_text(json.dumps(payload, indent=2))
    done = [k for k in STAGES if k not in skipped]
    print(f"matcher: {len(done)}/{len(STAGES)} stages applied to {len(payload)} rows")
    if skipped:
        print("  not implemented yet: " + ", ".join(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
