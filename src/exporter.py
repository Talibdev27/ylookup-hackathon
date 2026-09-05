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
import json

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

FLAG_HEADINGS = [
    "Check findings",
    "Check severity",
    "Check expected",
    "Check actual",
    "Check review action",
    "Check reviewer note",
]


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


def _display(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _flag_cells(flags: list[dict], decisions: dict) -> list[str]:
    """Six deterministic CSV cells for every check attached to one transaction."""
    ordered = sorted(flags, key=lambda flag: flag.get("flag_id", ""))
    actions = [decisions.get(flag.get("flag_id", ""), {}) for flag in ordered]
    return [
        "\n".join(_display(flag.get("message")) for flag in ordered),
        "\n".join(_display(flag.get("severity")) for flag in ordered),
        "\n".join(_display(flag.get("expected")) for flag in ordered),
        "\n".join(_display(flag.get("actual")) for flag in ordered),
        "\n".join(_display(answer.get("action")) for answer in actions),
        "\n".join(_display(answer.get("note")) for answer in actions),
    ]


def to_csv(
    rows: list[dict],
    decisions: dict,
    flags: list[dict] | None = None,
    flag_decisions: dict | None = None,
) -> str:
    """The whole queue as one sheet, including check findings and their disposition."""
    flags = flags or []
    flag_decisions = flag_decisions or {}
    keys = [key for key in STAGING_COLUMN if any(key in row.get("fields", {}) for row in rows)]
    by_row: dict[str, list[dict]] = {}
    for flag in flags:
        row_id = (flag.get("source") or {}).get("row_id")
        if row_id is not None:
            by_row.setdefault(str(row_id), []).append(flag)

    out = io.StringIO()
    writer = csv.writer(out)
    header = [name for name, _ in SOURCE_COLUMNS]
    for key in keys:
        heading = FIELD_HEADINGS.get(key, key)
        header += [heading, f"{heading} — decided by"]
    header += FLAG_HEADINGS
    writer.writerow(header)

    for row in rows:
        line = [read(row) for _, read in SOURCE_COLUMNS]
        for key in keys:
            line += list(_answer(row, decisions, key))
        line += _flag_cells(by_row.get(str(row["row_id"]), []), flag_decisions)
        writer.writerow(line)
    return out.getvalue()


def summary(
    rows: list[dict],
    decisions: dict,
    flags: list[dict] | None = None,
    flag_decisions: dict | None = None,
) -> dict[str, int]:
    """Unambiguous transaction and item counts for the queue and download button."""
    flags = flags or []
    flag_decisions = flag_decisions or {}
    flags_by_row: dict[str, list[dict]] = {}
    for flag in flags:
        row_id = (flag.get("source") or {}).get("row_id")
        if row_id is not None:
            flags_by_row.setdefault(str(row_id), []).append(flag)

    settled = 0
    outstanding = 0
    matcher_questions_total = 0
    matcher_questions_remaining = 0
    transactions_needing_matcher_review = 0
    automatically_settled = 0
    for row in rows:
        answered = decisions.get(str(row["row_id"])) or {}
        open_fields = [k for k, f in row.get("fields", {}).items() if f.get("status") != "auto"]
        row_flags = flags_by_row.get(str(row["row_id"]), [])
        matcher_questions_total += len(open_fields)
        matcher_questions_remaining += sum(1 for key in open_fields if key not in answered)
        if open_fields:
            transactions_needing_matcher_review += 1
        if not open_fields and not row_flags:
            automatically_settled += 1
            continue
        fields_done = all(key in answered for key in open_fields)
        flags_done = all(flag.get("flag_id") in flag_decisions for flag in row_flags)
        if fields_done and flags_done:
            settled += 1
        else:
            outstanding += 1

    flags_remaining = sum(
        1 for flag in flags if flag.get("flag_id") not in flag_decisions
    )
    return {
        "rows": len(rows),
        "reviewed": settled,
        "outstanding": outstanding,
        "automatically_settled_transactions": automatically_settled,
        "transactions_needing_matcher_review": transactions_needing_matcher_review,
        "matcher_questions_total": matcher_questions_total,
        "matcher_questions_remaining": matcher_questions_remaining,
        "automated_flags_found": len(flags),
        "automated_flags_remaining": flags_remaining,
        "total_review_items_remaining": matcher_questions_remaining + flags_remaining,
    }
