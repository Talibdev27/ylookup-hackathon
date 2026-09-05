"""Turn a reviewed queue into a file somebody can use.

Without this a reviewer clears seventy rows and has nothing to hand anyone, which is the
obvious question at the end of the demo: and then what?

One row per transaction, one column per answer, plus the columns that make it auditable --
where the value came from, and whether a person or the matcher decided it. CSV because the
people receiving it live in Excel, and because it needs no dependency to write.
"""
from __future__ import annotations

import csv
import io

from src.contract import STAGING_COLUMN

# The statement facts every row carries, in the order a reviewer reads them.
SOURCE_COLUMNS = [
    ("Statement", lambda row: row["source"].get("pdf", "")),
    ("Page", lambda row: row["source"].get("page", "")),
    ("Account", lambda row: row["raw"].get("account_name", "")),
    ("Account number", lambda row: row["raw"].get("account_number", "")),
    ("Value date", lambda row: row["raw"].get("value_date") or ""),
    ("Currency", lambda row: row["raw"].get("currency", "")),
    ("Credit", lambda row: row["raw"].get("credit") if row["raw"].get("credit") is not None else ""),
    ("Debit", lambda row: row["raw"].get("debit") if row["raw"].get("debit") is not None else ""),
    ("Bank narrative", lambda row: row["raw"].get("narrative_raw", "")),
]

# Human-readable heading per field, so the file reads like the screen rather than the code.
FIELD_HEADINGS = {
    "matched_legal_entity": "Fund",
    "pulled_out_project_code": "Project in bank text",
    "matched_project_code": "Project code",
    "pulled_out_sender_beneficiary": "Name in bank text",
    "matched_sender_beneficiary": "Counterparty",
    "classification": "Type",
    "cash_leg_transtype": "Cash side",
    "counterparty_transtype": "Other side",
    "resolved_deal": "Deal",
    "resolved_position": "Position",
}


def _answer(row: dict, decisions: dict, key: str) -> tuple[str, str]:
    """The final value for one field, and who settled it.

    A reviewer's decision always wins over the matcher's proposal -- including a decision
    to leave it unresolved, which clears the value rather than falling back to a guess the
    person has already rejected.
    """
    decided = (decisions.get(str(row["row_id"])) or {}).get(key)
    if decided:
        if decided["choice"] == "unresolved":
            return "", "reviewer: could not tell"
        return decided.get("value") or "", f"reviewer: {decided['choice']}"

    field = row.get("fields", {}).get(key)
    if not field:
        return "", ""
    if field.get("status") == "auto":
        return field.get("value") or "", "matcher"
    return field.get("value") or "", f"matcher: {field.get('status', 'unresolved')}"


def to_csv(rows: list[dict], decisions: dict) -> str:
    """The whole queue as one sheet. Fields present on any row become columns."""
    keys = [key for key in STAGING_COLUMN if any(key in row.get("fields", {}) for row in rows)]

    out = io.StringIO()
    writer = csv.writer(out)
    header = [name for name, _ in SOURCE_COLUMNS]
    for key in keys:
        heading = FIELD_HEADINGS.get(key, key)
        header += [heading, f"{heading} — decided by"]
    writer.writerow(header)

    for row in rows:
        line = [read(row) for _, read in SOURCE_COLUMNS]
        for key in keys:
            line += list(_answer(row, decisions, key))
        writer.writerow(line)
    return out.getvalue()


def summary(rows: list[dict], decisions: dict) -> dict[str, int]:
    """Counts for the download button, so a reviewer knows what they are about to export."""
    settled = 0
    outstanding = 0
    for row in rows:
        answered = decisions.get(str(row["row_id"])) or {}
        open_fields = [k for k, f in row.get("fields", {}).items() if f.get("status") != "auto"]
        if not open_fields:
            continue
        if all(k in answered for k in open_fields):
            settled += 1
        else:
            outstanding += 1
    return {"rows": len(rows), "reviewed": settled, "outstanding": outstanding}
