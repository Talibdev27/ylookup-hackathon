"""The flag contract. What the checking agent produces, whatever document it looked at.

Mirrors `src/contract.py`'s Field/Evidence on purpose: a flag is never a bare string,
because "inconsistent" with no citation is exactly the unchecked output the fund manager
in the interviews stopped trusting. `message` reaches a fund manager
verbatim, the way `Evidence.text` does for the matcher.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["info", "review", "error"]


@dataclass
class Flag:
    check: str  # which check raised this, e.g. "balance_continuity"
    severity: Severity
    message: str
    source: dict[str, Any] = field(default_factory=dict)
    expected: Any = None
    actual: Any = None
    flag_id: str = ""

    def __post_init__(self) -> None:
        """Give the finding a repeatable identity without relying on list position.

        A reviewer action is stored against this id.  It therefore includes both the
        source and the values that made the check fail: if a statement is corrected and
        either value moves, an old acknowledgement cannot silently attach to the new
        finding.
        """
        if self.flag_id:
            return
        payload = {
            "check": self.check,
            "source": self.source,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }
        encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        self.flag_id = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]
