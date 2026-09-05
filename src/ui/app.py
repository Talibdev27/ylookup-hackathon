"""The review queue.

The reader is a fund manager, not an engineer: no field keys, no confidence floats, no
raw currency codes reach the screen. Wording lives in `labels.py`.

The `Process` sheet in the client's own workbook is the spec -- six stages, each with a
review check. Rows the agent is confident about are hidden by default; what is left is
the work.

Run:  python3 serve.py
"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from src.ui import labels

app = Flask(__name__)
app.jinja_env.globals.update(
    label=labels.label,
    question=labels.question,
    money=labels.money,
    direction=labels.direction,
    pretty_date=labels.pretty_date,
    certainty=labels.certainty,
)

ROWS = Path("data/rows.json")
DECISIONS = Path("data/decisions.json")


def load_rows() -> list[dict]:
    return json.loads(ROWS.read_text()) if ROWS.exists() else []


def load_decisions() -> dict[str, dict]:
    return json.loads(DECISIONS.read_text()) if DECISIONS.exists() else {}


def save_decisions(decisions: dict[str, dict]) -> None:
    DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    DECISIONS.write_text(json.dumps(decisions, indent=2))


def open_questions(row: dict) -> list[tuple[str, dict]]:
    """The fields on this row that still need a human. Order follows the Process sheet."""
    return [(key, f) for key, f in row.get("fields", {}).items() if f.get("status") != "auto"]


@app.get("/")
def index():
    rows = load_rows()
    decisions = load_decisions()
    show_all = request.args.get("all") == "1"

    queue, done = [], 0
    for row in rows:
        questions = open_questions(row)
        settled = str(row["row_id"]) in decisions
        if settled:
            done += 1
        if not questions:
            continue
        if settled and not show_all:
            continue
        queue.append({"row": row, "questions": questions, "decision": decisions.get(str(row["row_id"]))})

    needs_review = sum(1 for r in rows if open_questions(r))
    return render_template(
        "review.html",
        queue=queue,
        show_all=show_all,
        total=len(rows),
        needs_review=needs_review,
        reviewed=done,
        remaining=needs_review - done,
        confident=len(rows) - needs_review,
    )


@app.post("/rows/<int:row_id>/decide")
def decide(row_id: int):
    payload = request.get_json(silent=True) or request.form
    choice = payload.get("choice")
    if choice not in {"approve", "alternative"}:
        return jsonify({"error": "choice must be 'approve' or 'alternative'"}), 400

    decisions = load_decisions()
    decisions[str(row_id)] = {
        "choice": choice,
        "field": payload.get("field"),
        "value": payload.get("value"),
    }
    save_decisions(decisions)

    if request.is_json:
        return jsonify({"row_id": row_id, "choice": choice, "reviewed": len(decisions)})
    return redirect(url_for("index"))


@app.post("/reset")
def reset():
    save_decisions({})
    return redirect(url_for("index"))
