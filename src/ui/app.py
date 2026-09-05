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
from datetime import datetime, timezone
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
    check_label=labels.check_label,
    severity_label=labels.severity_label,
    flag_action_label=labels.flag_action_label,
    value_preview=labels.value_preview,
    is_long_value=labels.is_long_value,
)

# The pipeline owns where these live and when they are invalidated.
ROWS = pipeline.ROWS
DECISIONS = pipeline.DECISIONS
FLAGS = pipeline.FLAGS
FLAG_DECISIONS = pipeline.FLAG_DECISIONS

FLAG_ACTIONS = {"acknowledge", "resolved", "false_positive"}
MAX_FLAG_NOTE = 1000


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


def load_flag_report() -> dict:
    """Persisted check results, including proof that a clean check actually ran."""
    empty = {
        "checks_total": 0,
        "checks_applied": [],
        "check_failures": {},
        "flags_found": 0,
        "flags": [],
    }
    if not FLAGS.exists():
        return empty
    loaded = json.loads(FLAGS.read_text())
    if not isinstance(loaded, dict):
        return empty
    return {**empty, **loaded}


def load_flag_decisions() -> dict[str, dict]:
    return json.loads(FLAG_DECISIONS.read_text()) if FLAG_DECISIONS.exists() else {}


def save_flag_decisions(decisions: dict[str, dict]) -> None:
    FLAG_DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    FLAG_DECISIONS.write_text(json.dumps(decisions, indent=2))


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
    if entry.get("flags"):
        group = 0
    elif flagged_discrepancy(row):
        group = 1
    else:
        group = 2
    return (group, -amount(row))


def _safe_source(source: dict | None) -> dict:
    """The source facts a browser needs, never a server-side filesystem path."""
    source = source or {}
    safe = {
        key: source.get(key)
        for key in ("pdf", "page", "row_id", "account")
        if key in source
    }
    if safe.get("pdf"):
        safe["pdf"] = Path(str(safe["pdf"])).name
    return safe


def _public_flag(flag: dict, decision: dict | None = None) -> dict:
    return {
        "flag_id": flag.get("flag_id", ""),
        "check": flag.get("check", ""),
        "label": labels.check_label(flag.get("check", "")),
        "severity": flag.get("severity", "review"),
        "severity_label": labels.severity_label(flag.get("severity", "review")),
        "message": flag.get("message", ""),
        "source": _safe_source(flag.get("source")),
        "expected": flag.get("expected"),
        "actual": flag.get("actual"),
        "decision": decision,
    }


def _public_check_status(report: dict) -> dict:
    failures = report.get("check_failures") or {}
    return {
        "checks_total": report.get("checks_total", 0),
        "checks_executed": len(report.get("checks_applied") or []),
        "checks_failed": sum(failures.values()),
        "completed": [
            {"check": name, "label": labels.check_label(name), "status": "completed"}
            for name in report.get("checks_applied") or []
        ],
        "failed": [
            {
                "check": name.split(" (", 1)[0],
                "label": labels.check_label(name.split(" (", 1)[0]),
                "status": "failed",
            }
            for name in failures
        ],
        "flags_found": report.get("flags_found", len(report.get("flags") or [])),
    }


def review_state(show_all: bool = False) -> dict:
    """One queue and one set of counts for matcher questions and check findings."""
    rows = load_rows()
    decisions = load_decisions()
    report = load_flag_report()
    flags = report.get("flags") or []
    flag_decisions = load_flag_decisions()

    by_row: dict[str, list[dict]] = {}
    unattached = []
    known_rows = {str(row["row_id"]) for row in rows}
    for flag in flags:
        row_id = (flag.get("source") or {}).get("row_id")
        if row_id is None or str(row_id) not in known_rows:
            decision = flag_decisions.get(flag.get("flag_id", ""))
            if show_all or not decision:
                unattached.append(_public_flag(flag, decision))
        else:
            by_row.setdefault(str(row_id), []).append(flag)

    queue = []
    for row in rows:
        row_key = str(row["row_id"])
        questions = open_questions(row)
        row_flags = sorted(by_row.get(row_key, []), key=lambda flag: flag.get("flag_id", ""))
        if not questions and not row_flags:
            continue
        answered = decisions.get(row_key, {})
        public_flags = [
            _public_flag(flag, flag_decisions.get(flag.get("flag_id", ""))) for flag in row_flags
        ]
        settled = all(key in answered for key, _ in questions) and all(
            flag["decision"] for flag in public_flags
        )
        if settled and not show_all:
            continue
        queue.append(
            {
                "row": row,
                "questions": questions,
                "answered": answered,
                "flags": public_flags,
                "settled": settled,
            }
        )
    queue.sort(key=queue_rank)

    counts = exporter.summary(rows, decisions, flags, flag_decisions)
    counts.update(
        {
            "automated_checks_total": report.get("checks_total", 0),
            "automated_checks_executed": len(report.get("checks_applied") or []),
            "automated_checks_failed": sum((report.get("check_failures") or {}).values()),
            "transactions_remaining": counts["outstanding"],
            "reviewed_transactions": counts["reviewed"],
            "total_review_items": counts["matcher_questions_total"] + len(flags),
        }
    )
    return {
        "rows": rows,
        "queue": queue,
        "unattached_flags": unattached,
        "summary": counts,
        "checks": _public_check_status(report),
        "report": report,
    }


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
    show_all = request.args.get("all") == "1"
    state = review_state(show_all)
    rows = state["rows"]
    return render_template(
        "review.html",
        queue=state["queue"],
        unattached_flags=state["unattached_flags"],
        show_all=show_all,
        total=len(rows),
        summary=state["summary"],
        checks=state["checks"],
        space=workspace.current(),
        suggestions=counterparty_suggestions(),
        # No rows at all is not the same as everything reviewed. On a fresh deployment
        # the difference is the whole first impression: one says the product has nothing
        # to do, the other says it is waiting for your statements.
        has_data=bool(rows),
        export=state["summary"],
    )


@app.get("/api/review")
def api_review():
    """Stable Stage D data for a separate frontend, without server filesystem paths."""
    state = review_state(request.args.get("all") == "1")
    items = []
    for entry in state["queue"]:
        row = entry["row"]
        questions = []
        for key, field in entry["questions"]:
            questions.append(
                {
                    "field": key,
                    "label": labels.label(key),
                    "question": labels.question(key),
                    **field,
                    "decision": entry["answered"].get(key),
                }
            )
        items.append(
            {
                "transaction": {
                    "row_id": row["row_id"],
                    "source": _safe_source(row.get("source")),
                    "raw": row.get("raw") or {},
                },
                "matcher_questions": questions,
                "automated_flags": entry["flags"],
                "settled": entry["settled"],
            }
        )
    return jsonify(
        {
            "summary": state["summary"],
            "checks": state["checks"],
            "items": items,
            "unattached_flags": state["unattached_flags"],
        }
    )


@app.get("/export.csv")
def export_csv():
    """The reviewed queue as a file. Everything, not just the rows that were checked --
    the 28 the matcher was confident about are answers too, and a part-reviewed export is
    still useful."""
    rows = load_rows()
    if not rows:
        return redirect(url_for("upload_form", error="There is nothing to export yet."))
    report = load_flag_report()
    body = exporter.to_csv(
        rows,
        load_decisions(),
        report.get("flags") or [],
        load_flag_decisions(),
    )
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


@app.post("/api/flags/<flag_id>/decide")
def decide_flag(flag_id: str):
    """Record an auditable disposition without mixing it into field decisions."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "a flag decision must be JSON"}), 400
    action = payload.get("action")
    if action not in FLAG_ACTIONS:
        return jsonify({"error": f"unknown flag action {action!r}"}), 400
    note = payload.get("note", "")
    if not isinstance(note, str):
        return jsonify({"error": "the reviewer note must be text"}), 400
    note = note.strip()
    if len(note) > MAX_FLAG_NOTE:
        return jsonify(
            {"error": f"the reviewer note must be {MAX_FLAG_NOTE} characters or fewer"}
        ), 400

    flags = load_flag_report().get("flags") or []
    found = next((flag for flag in flags if flag.get("flag_id") == flag_id), None)
    if found is None:
        return jsonify({"error": "flag not found"}), 404

    decisions = load_flag_decisions()
    decisions[flag_id] = {
        "action": action,
        "note": note,
        "source": _safe_source(found.get("source")),
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    save_flag_decisions(decisions)
    return jsonify({"flag_id": flag_id, "action": action, "note": note})


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
    save_flag_decisions({})
    return redirect(url_for("index"))
