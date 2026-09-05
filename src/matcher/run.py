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

ROWS = Path("data/rows.json")

# field key -> (callable, extra kwargs drawn from the spine)
STAGES = {
    "cash_leg_transtype": stages.cash_leg_transtype,
    "matched_legal_entity": stages.matched_legal_entity,
    "pulled_out_sender_beneficiary": stages.pulled_out_sender_beneficiary,
    "matched_sender_beneficiary": stages.matched_sender_beneficiary,
    "matched_project_code": stages.matched_project_code,
    "classification": stages.classification,
    "resolved_position": stages.resolved_position,
}


def apply_stages(payload: list[dict]) -> tuple[list[dict], list[str]]:
    skipped: list[str] = []
    for entry in payload:
        row = Row(row_id=entry["row_id"], source=entry["source"], raw=Raw(**entry["raw"]))
        for key, stage in STAGES.items():
            try:
                field = stage(row)
            except NotImplementedError:
                if key not in skipped:
                    skipped.append(key)
                continue
            except TypeError:
                # stage needs master-list arguments it has not been wired to yet
                if key not in skipped:
                    skipped.append(key)
                continue
            entry.setdefault("fields", {})[key] = asdict(field)
    return payload, skipped


def main() -> int:
    payload = json.loads(ROWS.read_text())
    payload, skipped = apply_stages(payload)
    ROWS.write_text(json.dumps(payload, indent=2))
    done = [k for k in STAGES if k not in skipped]
    print(f"matcher: {len(done)}/{len(STAGES)} stages applied to {len(payload)} rows")
    if skipped:
        print("  not implemented yet: " + ", ".join(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
