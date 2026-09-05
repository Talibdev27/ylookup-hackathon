"""Score matcher output against the 100 human ground-truth rows in `Staging Sheet`.

Two numbers matter and they answer different questions:

  agreement  -- of the rows the human filled, how many do we reproduce exactly?
  net new    -- of the rows the human left blank, how many do we resolve?

The second is the pitch. The human left 52 of 100 counterparties unmatched.

Alignment note: the parsed rows come out in statement-filename order and the staging
sheet is in its own order -- only 11 of 100 line up by position. Comparing by index
silently scores the wrong pairs, so rows are joined on a key.

That key includes the account number, which is not optional: an inter-fund transfer is
written on both statements with the same narrative, the same amount and the same bank
reference, so a key without the account pairs the two sides crosswise. It showed up as
three legal entities in a rotating three-cycle, which reads like a matcher bug and is
not one.

Usage:  python -m src.matcher.score data/rows.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from src.contract import STAGING_COLUMN
from src.spine.build import WORKBOOK, load_workbook

Key = tuple[str, str, str, str]


def _norm(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _truth_key(record: dict[str, str]) -> Key:
    for column in ("Credit amount", "Debit amount"):
        raw = (record.get(column) or "").strip()
        if raw:
            amount = f"{float(raw):.2f}"
            break
    else:
        amount = ""
    return (
        _norm(record["Narrative"]),
        amount,
        _norm(record["Bank reference"]),
        _norm(record["Account Number"]),
    )


def _row_key(row: dict) -> Key:
    raw = row["raw"]
    value = raw["credit"] if raw["credit"] is not None else raw["debit"]
    amount = f"{value:.2f}" if value is not None else ""
    return (
        _norm(raw["narrative_raw"]),
        amount,
        _norm(raw["bank_reference"]),
        _norm(raw["account_number"]),
    )


def align(rows: list[dict], truth: list[dict[str, str]]) -> list[tuple[dict, dict[str, str]]]:
    """Pair each parsed row with its ground-truth record. Unmatched rows are dropped and
    reported by the caller -- silently scoring an unaligned pair is worse than a gap."""
    buckets: dict[Key, list[dict[str, str]]] = defaultdict(list)
    for record in truth:
        buckets[_truth_key(record)].append(record)
    pairs = []
    for row in rows:
        candidates = buckets.get(_row_key(row))
        if candidates:
            pairs.append((row, candidates.pop(0)))
    return pairs


def score(pairs: list[tuple[dict, dict[str, str]]]) -> dict[str, dict[str, int]]:
    report: dict[str, dict[str, int]] = {}
    for key, column in STAGING_COLUMN.items():
        stats = {"human_filled": 0, "human_blank": 0, "agree": 0, "disagree": 0, "net_new": 0}
        for row, record in pairs:
            expected = (record.get(column) or "").strip()
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
    truth = load_workbook(WORKBOOK)["Staging Sheet"]
    pairs = align(rows, truth)
    if len(pairs) != len(rows):
        print(f"warning: {len(rows) - len(pairs)} rows did not align to ground truth", file=sys.stderr)

    report = score(pairs)
    print(f"{'field':32s} {'agree/filled':>14s} {'wrong':>6s} {'new/blank':>12s}")
    print("-" * 68)
    for key, s in report.items():
        agreement = "{}/{}".format(s["agree"], s["human_filled"])
        net_new = "{}/{}".format(s["net_new"], s["human_blank"])
        print(f"{key:32s} {agreement:>14s} {s['disagree']:>6d} {net_new:>12s}")

    print(f"\naligned {len(pairs)}/{len(rows)} rows against ground truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
