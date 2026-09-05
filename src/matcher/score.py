"""Score matcher output against the 100 human ground-truth rows in `Staging Sheet`.

Two numbers matter and they are different questions:

  agreement  -- of the rows the human filled, how many do we match exactly?
  net new    -- of the rows the human left blank, how many do we resolve?

The second is the whole pitch. The human left 52 of 100 counterparties unmatched.

Usage:  python -m src.matcher.score data/rows.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.contract import STAGING_COLUMN
from src.spine.xlsx import Workbook

WORKBOOK = Path(
    "/Users/muhammadaminesaev/Downloads/Ylookup Hackathon Datasets/"
    "01-bank-statements-to-journal-entries/workbook/"
    "Bank statement to journal entries - working file (anonymised).xlsx"
)


def load_truth(workbook_path: Path = WORKBOOK) -> list[dict[str, str]]:
    return Workbook(str(workbook_path)).records("Staging Sheet")


def score(rows: list[dict], truth: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    report: dict[str, dict[str, int]] = {}
    for key, column in STAGING_COLUMN.items():
        stats = {"human_filled": 0, "human_blank": 0, "agree": 0, "disagree": 0, "net_new": 0}
        for row, expected_row in zip(rows, truth):
            expected = (expected_row.get(column) or "").strip()
            got = ((row.get("fields", {}).get(key) or {}).get("value") or "").strip()
            if expected:
                stats["human_filled"] += 1
                if got == expected:
                    stats["agree"] += 1
                elif got:
                    stats["disagree"] += 1
            else:
                stats["human_blank"] += 1
                if got:
                    stats["net_new"] += 1
        report[key] = stats
    return report


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/rows.json")
    if not path.exists():
        print(f"no {path} yet -- run `python -m src.spine.build` first", file=sys.stderr)
        return 1
    rows = json.loads(path.read_text())
    truth = load_truth()
    if len(rows) != len(truth):
        print(f"warning: {len(rows)} rows vs {len(truth)} ground-truth rows", file=sys.stderr)

    report = score(rows, truth)
    print(f"{'field':32s} {'agree/filled':>14s} {'wrong':>6s} {'new/blank':>12s}")
    print("-" * 68)
    for key, s in report.items():
        agreement = f"{s['agree']}/{s['human_filled']}"
        net_new = f"{s['net_new']}/{s['human_blank']}"
        print(f"{key:32s} {agreement:>14s} {s['disagree']:>6d} {net_new:>12s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
