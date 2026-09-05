"""Bank statement PDF -> transaction rows.  W1 owns this.

Filenames encode the metadata, e.g.
    20260331_NI_V_SCSP_CALDER_EUR_030041.pdf
    ^date    ^entity      ^bank  ^ccy ^account short code

Seven statements, four currencies (EUR, USD, GBP, DKK), six business days.

Watch for: narratives wrap across lines mid-word, with commas at the wrap points. Keep
the wrapped form as `narrative_raw` -- evidence spans in the review UI index into it.
"""
from __future__ import annotations

import re
from pathlib import Path

FILENAME = re.compile(
    r"^(?P<date>\d{8})_(?P<entity>.+)_(?P<bank>[A-Z]+)_(?P<currency>[A-Z]{3})_(?P<account>\w+)\.pdf$"
)


def parse_filename(path: Path) -> dict[str, str]:
    match = FILENAME.match(path.name)
    if not match:
        raise ValueError(f"unexpected statement filename: {path.name}")
    parts = match.groupdict()
    parts["entity"] = parts["entity"].replace("_", " ").strip()
    return parts
