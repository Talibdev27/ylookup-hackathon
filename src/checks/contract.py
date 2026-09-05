"""The flag contract. What the checking agent produces, whatever document it looked at.

Mirrors `src/contract.py`'s Field/Evidence on purpose: a flag is never a bare string,
because "inconsistent" with no citation is exactly the unchecked output the fund manager
in the interviews stopped trusting -- see CONTEXT.md. `message` reaches a fund manager
verbatim, the way `Evidence.text` does for the matcher.
"""
from __future__ import annotations

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
