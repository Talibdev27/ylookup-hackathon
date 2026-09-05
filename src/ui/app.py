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

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from src import exporter, pipeline
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

# The pipeline owns where these live and when they are invalidated.
ROWS = pipeline.ROWS
DECISIONS = pipeline.DECISIONS


def load_rows() -> list[dict]:
    return json.loads(ROWS.read_text()) if ROWS.exists() else []


def load_decisions() -> dict[str, dict[str, dict]]:
    """Decisions, keyed by row and then by field.

    Keyed by row alone at first, which was wrong: 21 of the 72 rows in the queue ask more
    than one question, so answering the second overwrote the answer to the first.
    """
    return json.loads(DECISIONS.read_text()) if DECISIONS.exists() else {}


def save_decisions(decisions: dict[str, dict]) -> None:
    DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    DECISIONS.write_text(json.dumps(decisions, indent=2))


def open_questions(row: dict) -> list[tuple[str, dict]]:
    """The fields on this row that still need a human. Order follows the Process sheet."""
    return [(key, f) for key, f in row.get("fields", {}).items() if f.get("status") != "auto"]


def flagged_discrepancy(row: dict) -> bool:
    """True when the client's documented rule contradicts their own booking.

    ADR 0001: the `Process` sheet books a credit row to `Cash - Received`, and every row
    in the working file is booked `Cash - Disbursed`. `cash_leg_transtype` reproduces the
    file and marks the disagreement rather than silently agreeing with it, so a cash leg
    that is not `auto` is exactly one of those rows. Reading the status keeps this honest
    about where the flag comes from; matching on the evidence wording would break the
    moment somebody improves the sentence.
    """
    field = row.get("fields", {}).get("cash_leg_transtype") or {}
    return field.get("status", "auto") != "auto"


def amount(row: dict) -> float:
    """What the payment is worth, whichever side it landed on."""
    raw = row.get("raw") or {}
    return abs(raw.get("credit") or raw.get("debit") or 0.0)


def queue_rank(entry: dict) -> tuple[int, float]:
    """Reviewer attention is the scarce thing, so spend it in order of what it is worth.

    Statement order opened the queue on a 44-cent bank charge asking four questions it
    could not answer, and left the seven-figure rows carrying the Process-sheet
    contradiction below the fold. Flagged rows first, then by amount: the reviewer meets
    the rows where we have something to tell them before the ones where we are only
    asking. Presentation only -- decisions are keyed by row, so nothing downstream can
    notice the order.
    """
    row = entry["row"]
    return (0 if flagged_discrepancy(row) else 1, -amount(row))


def counterparty_suggestions() -> list[str]:
    """Every name a counterparty could legitimately be.

    A reviewer correcting a row should be choosing a real entry from their own reference
    lists, not typing free text that will never resolve. Free text is still allowed --
    they may know something the lists do not -- but the offered options are real.
    """
    from src.matcher.reference import ReferenceLists
    from src.spine.build import load_workbook

    try:
        lists = ReferenceLists.from_workbook(load_workbook())
    except SystemExit:
        return []
    names: set[str] = set()
    for _, entries in lists.counterparty_lists():
        names.update(entries)
    return sorted(names)


@app.get("/")
def index():
    rows = load_rows()
    decisions = load_decisions()
    show_all = request.args.get("all") == "1"

    queue, done = [], 0
    for row in rows:
        questions = open_questions(row)
        if not questions:
            continue
        answered = decisions.get(str(row["row_id"]), {})
        settled = all(key in answered for key, _ in questions)
        if settled:
            done += 1
            if not show_all:
                continue
        queue.append({"row": row, "questions": questions, "answered": answered})

    queue.sort(key=queue_rank)

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
        suggestions=counterparty_suggestions(),
        # No rows at all is not the same as everything reviewed. On a fresh deployment
        # the difference is the whole first impression: one says the product has nothing
        # to do, the other says it is waiting for your statements.
        has_data=bool(rows),
        export=exporter.summary(rows, decisions),
    )


@app.get("/export.csv")
def export_csv():
    """The reviewed queue as a file. Everything, not just the rows that were checked --
    the 28 the matcher was confident about are answers too, and a part-reviewed export is
    still useful."""
    rows = load_rows()
    if not rows:
        return redirect(url_for("upload_form", error="There is nothing to export yet."))
    body = exporter.to_csv(rows, load_decisions())
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="reviewed-transactions.csv"'},
    )


@app.post("/rows/<int:row_id>/decide")
def decide(row_id: int):
    payload = request.get_json(silent=True) or request.form
    choice = payload.get("choice")
    if choice not in {"approve", "alternative", "manual", "unresolved"}:
        return jsonify({"error": f"unknown choice {choice!r}"}), 400

    value = (payload.get("value") or "").strip()
    if choice == "manual" and not value:
        return jsonify({"error": "a correction needs a value"}), 400
    if choice == "unresolved":
        # The reviewer could not work it out either. That is a real answer and it has to
        # be recordable -- otherwise the row sits in the queue forever and the count
        # never reaches zero.
        value = ""

    field = payload.get("field")
    if not field:
        return jsonify({"error": "a decision has to say which field it answers"}), 400

    decisions = load_decisions()
    decisions.setdefault(str(row_id), {})[field] = {"choice": choice, "value": value}
    save_decisions(decisions)

    if request.is_json:
        return jsonify({"row_id": row_id, "field": field, "choice": choice})
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
    pipeline.run(workspace.current())


@app.post("/reset")
def reset():
    save_decisions({})
    return redirect(url_for("index"))
