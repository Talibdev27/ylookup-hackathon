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
import tempfile
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from src.spine import workspace
from src.ui import labels

# A bank statement is tens of kilobytes; a reference workbook a few megabytes. Anything
# far outside that is not what the person thinks they are uploading.
MAX_UPLOAD_BYTES = 64 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
app.jinja_env.globals.update(
    label=labels.label,
    question=labels.question,
    money=labels.money,
    direction=labels.direction,
    pretty_date=labels.pretty_date,
    certainty=labels.certainty,
    statement_label=labels.statement_label,
    highlight=labels.highlight,
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
        space=workspace.current(),
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


@app.get("/upload")
def upload_form():
    space = workspace.current()
    return render_template(
        "upload.html",
        space=space,
        statement_count=len(space.statement_files),
        error=request.args.get("error"),
    )


@app.post("/upload")
def upload():
    """Take this week's statements, and a reference workbook if one is not set up yet.

    The pipeline runs synchronously: seven statements parse in a couple of seconds, and a
    progress bar for a two-second job is a worse experience than waiting for it.
    """
    statements = [f for f in request.files.getlist("statements") if f.filename]
    workbook = request.files.get("workbook")
    has_workbook = bool(workbook and workbook.filename)

    if not statements:
        return redirect(url_for("upload_form", error="Choose at least one bank statement to upload."))
    bad = [f.filename for f in statements if not f.filename.lower().endswith(".pdf")]
    if bad:
        return redirect(url_for("upload_form",
                                error=f"Bank statements have to be PDFs. This one is not: {bad[0]}"))
    if has_workbook and not workbook.filename.lower().endswith((".xlsx", ".xlsm")):
        return redirect(url_for("upload_form",
                                error="The reference lists have to be an Excel file (.xlsx)."))
    if not has_workbook and workspace.current().workbook is None:
        return redirect(url_for("upload_form",
                                error="No reference lists are set up yet, so one has to be uploaded too."))

    if has_workbook:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as staged:
            workbook.save(staged.name)
        workspace.save_workbook(Path(staged.name))
        Path(staged.name).unlink(missing_ok=True)

    target = workspace.clear_statements()
    for statement in statements:
        statement.save(target / secure_filename(statement.filename))

    try:
        rebuild()
    except (SystemExit, AssertionError, ValueError) as failure:
        return redirect(url_for("upload_form", error=str(failure)))
    return redirect(url_for("index"))


def rebuild() -> None:
    """Re-run the pipeline over whatever is now in the workspace."""
    from src.matcher.run import apply_stages, load_lists
    from src.spine.build import load_workbook, parse_statements, write_sqlite
    from src.matcher.normalise import normalise

    space = workspace.current()
    sheets = load_workbook(space.workbook)
    write_sqlite(sheets)
    rows = parse_statements(space.statements)
    for row in rows:
        row.raw.narrative_normalised, _ = normalise(row.raw.narrative_raw)
    payload = [r.to_dict() for r in rows]
    payload, _, _ = apply_stages(payload, load_lists())
    ROWS.parent.mkdir(parents=True, exist_ok=True)
    ROWS.write_text(json.dumps(payload, indent=2))
    DECISIONS.unlink(missing_ok=True)


@app.post("/reset")
def reset():
    save_decisions({})
    return redirect(url_for("index"))
