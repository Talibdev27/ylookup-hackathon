"""Run every automated consistency check without confusing silence with failure.

Checks are deliberately smaller than matcher stages: each one receives the extracted
rows and returns findings.  This runner owns orchestration, failure isolation and the
execution facts persisted for the review queue.
"""
from __future__ import annotations

import traceback
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from src.checks import currency_mismatch, duplicates, footing, round_numbers
from src.checks.contract import Flag
from src.contract import Row

Check = Callable[[list[Row]], list[Flag]]

REGISTRY: list[tuple[str, Check]] = [
    ("balance_continuity", footing.check),
    ("duplicate_transaction", duplicates.check),
    ("round_number_amount", round_numbers.check),
    ("currency_mismatch", currency_mismatch.check),
]


@dataclass
class CheckResult:
    checks_total: int
    checks_applied: list[str] = field(default_factory=list)
    failures: Counter = field(default_factory=Counter)
    flags: list[Flag] = field(default_factory=list)

    @property
    def checks_applied_count(self) -> int:
        return len(self.checks_applied)


def apply_checks(
    rows: list[Row], registry: list[tuple[str, Check]] | None = None
) -> CheckResult:
    """Run checks independently so one defect never drops the transaction queue."""
    selected = REGISTRY if registry is None else registry
    result = CheckResult(checks_total=len(selected))
    seen_ids: Counter = Counter()

    for name, check in selected:
        try:
            produced = list(check(rows))
            if any(not isinstance(flag, Flag) for flag in produced):
                raise TypeError("checks must return Flag objects")
        except Exception as error:  # a broken check is reported, not presented as clean
            traceback.print_exc()
            result.failures[f"{name} ({type(error).__name__})"] += 1
            continue

        result.checks_applied.append(name)
        for flag in produced:
            # Two checks should not normally emit the exact same finding.  If one does,
            # keep both reviewable rather than letting their decisions overwrite.
            seen_ids[flag.flag_id] += 1
            if seen_ids[flag.flag_id] > 1:
                flag.flag_id = f"{flag.flag_id}-{seen_ids[flag.flag_id]}"
            result.flags.append(flag)

    return result
