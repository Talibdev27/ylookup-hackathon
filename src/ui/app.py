"""Review queue.  W3 owns this.

The `Process` sheet in the client's own workbook is the spec: six stages, each with its
own review check. Default view is exceptions only -- the 52 unresolved counterparties,
the 30 rows with no project match, the 3 flagged Review. Nobody wants to scroll 100 rows.

Run:  flask --app src.ui.app run --port 5001
"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
ROWS = Path("data/rows.json")

# Stage -> the fields reviewed at that stage, from the Process sheet.
STAGES = {
    "2. Counterparty": ["pulled_out_sender_beneficiary", "matched_legal_entity"],
    "3. Project code": ["pulled_out_project_code", "matched_project_code"],
    "4. Classification": ["matched_sender_beneficiary", "classification", "counterparty_transtype", "cash_leg_transtype"],
    "5. Position": ["resolved_deal", "resolved_position"],
}


def load_rows() -> list[dict]:
    if not ROWS.exists():
        return []
    return json.loads(ROWS.read_text())


def needs_attention(row: dict) -> bool:
    return any(f.get("status") != "auto" for f in row.get("fields", {}).values())


@app.get("/")
def index():
    rows = load_rows()
    exceptions_only = request.args.get("all") != "1"
    shown = [r for r in rows if needs_attention(r)] if exceptions_only else rows
    counts = {
        "auto": sum(1 for r in rows if not needs_attention(r)),
        "remaining": sum(1 for r in rows if needs_attention(r)),
        "total": len(rows),
    }
    return render_template("review.html", rows=shown, counts=counts, stages=STAGES)


@app.post("/rows/<int:row_id>/decide")
def decide(row_id: int):
    """Record approve / reject / correct. W3: persist to data/decisions.json."""
    return jsonify({"row_id": row_id, "ok": False, "error": "not implemented"}), 501
