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
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from src import exporter, pipeline
from src.gl_migration import analyze as gl_migration
from src.gl_migration import workspace as gl_workspace
from src.reports import statements as report_statements
from src.spine import workspace
from src.ui import labels

# A bank statement is tens of kilobytes; a reference workbook a few megabytes. Anything
# far outside that is not what the person thinks they are uploading.
MAX_UPLOAD_BYTES = 64 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


# Every route a cross-origin frontend actually calls. Not just /api/*: /rows/<id>/decide
# predates the /api prefix and was kept at its original path deliberately (see
# FRONTEND-HANDOFF.md, "existing route preserved") for the server-rendered UI, which
# means it needs this header too, or a browser fetch to it fails before Flask ever sees
# it -- caught by actually clicking the button in a real browser, not just curling it
# server-side, which has no CORS to enforce in the first place.
CROSS_ORIGIN_PREFIXES = ("/api/", "/rows/")


@app.after_request
def _allow_cross_origin_reads(response):
    """The Next.js frontend runs as its own server on its own origin -- localhost:3000
    talking to this app's localhost:5001 in dev, and its own deployed URL talking to
    this app's Render URL in production. Neither is the same origin as this Flask app,
    so a browser blocks the fetch entirely without this header. Server-rendered pages
    under `/` are navigated to directly, never fetched cross-origin, and don't need it.
    """
    if request.path.startswith(CROSS_ORIGIN_PREFIXES):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


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

# The demo video, once one exists. Paste the link here, or set YLOOKUP_VIDEO_URL on the
# host. Until then the front page offers no video at all rather than a link that goes
# nowhere -- everything it says stands on its own without one.
VIDEO_URL = os.environ.get("YLOOKUP_VIDEO_URL") or None

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


def _matched_entity(row: dict) -> str | None:
    """The matcher's resolved fund name for this row, `auto` or not.

    `matcher_questions` in the public API only carries non-auto fields, and
    `matched_legal_entity` is auto on the bundled sample every time -- 100/100 -- so it
    never appears there. Filtering by company needs the value regardless of status.
    """
    field = row.get("fields", {}).get("matched_legal_entity") or {}
    return field.get("value")


def review_state(show_all: bool = False, legal_entity: str | None = None) -> dict:
    """One queue and one set of counts for matcher questions and check findings.

    `legal_entity`, when given, scopes everything -- queue, unattached flags, and the
    summary counts -- to one fund's transactions. None means the whole dataset, which is
    what the server-rendered page at `/` always shows.
    """
    rows = load_rows()
    if legal_entity:
        rows = [row for row in rows if _matched_entity(row) == legal_entity]
    decisions = load_decisions()
    report = load_flag_report()
    flags = report.get("flags") or []
    flag_decisions = load_flag_decisions()

    by_row: dict[str, list[dict]] = {}
    unattached = []
    known_rows = {str(row["row_id"]) for row in rows}
    for flag in flags:
        row_id = (flag.get("source") or {}).get("row_id")
        row_id_str = str(row_id) if row_id is not None else None
        if row_id_str is not None and row_id_str in known_rows:
            by_row.setdefault(row_id_str, []).append(flag)
            continue
        if row_id_str is not None and legal_entity:
            # A real finding, just on a different company's transaction -- not this
            # view's business, unattached or not.
            continue
        decision = flag_decisions.get(flag.get("flag_id", ""))
        if show_all or not decision:
            unattached.append(_public_flag(flag, decision))

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
        # Counted, never hardcoded: on the sample data this is the 23 rows of ADR 0001,
        # but a client's own statements will have their own number, or none.
        flagged=sum(1 for r in rows if flagged_discrepancy(r)),
        video_url=VIDEO_URL,
        # No rows at all is not the same as everything reviewed. On a fresh deployment
        # the difference is the whole first impression: one says the product has nothing
        # to do, the other says it is waiting for your statements.
        has_data=bool(rows),
        export=state["summary"],
    )


@app.get("/api/review")
def api_review():
    """Stable Stage D data for a separate frontend, without server filesystem paths.

    `?company=<id>` scopes the queue to one fund -- the same ids `/api/companies`
    returns -- for a per-company review tab. Omitted, this is the whole dataset.
    """
    company_id = request.args.get("company")
    legal_entity = _entities_by_slug().get(company_id) if company_id else None
    if company_id and not legal_entity:
        return jsonify({"error": f"no company {company_id!r}"}), 404
    state = review_state(request.args.get("all") == "1", legal_entity=legal_entity)
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


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _diu_and_coa() -> tuple[list[dict], list[dict]] | None:
    """The two sheets `src/reports/statements.py` needs, or None if no workbook is set
    up yet -- callers decide what that means for their own response."""
    from src.spine.build import load_workbook

    try:
        sheets = load_workbook()
    except SystemExit:
        return None
    diu_name = next((name for name in sheets if name.strip() == "DIU"), None)
    if diu_name is None or "CoA" not in sheets:
        return None
    return sheets[diu_name], sheets["CoA"]


def _entities_by_slug() -> dict[str, str]:
    loaded = _diu_and_coa()
    if not loaded:
        return {}
    diu, _ = loaded
    return {_slug(name): name for name in report_statements.legal_entities(diu)}


@app.get("/api/companies")
def api_companies():
    """The funds with journal activity in the reference workbook -- the closest thing
    this data has to "companies" for a per-entity financial-statement view. Not the
    matcher's output: see src/reports/statements.py for why this reads DIU/CoA directly.
    """
    entities = _entities_by_slug()
    return jsonify(
        {
            "companies": [
                {"id": slug, "name": name}
                for slug, name in sorted(entities.items(), key=lambda pair: pair[1])
            ]
        }
    )


@app.get("/api/companies/<company_id>/balance-sheet")
def api_balance_sheet(company_id: str):
    loaded = _diu_and_coa()
    if not loaded:
        return jsonify({"error": "no reference workbook is set up yet"}), 404
    entity = _entities_by_slug().get(company_id)
    if not entity:
        return jsonify({"error": f"no company {company_id!r}"}), 404
    diu, coa = loaded
    return jsonify(report_statements.balance_sheet(diu, coa, legal_entity=entity))


@app.get("/api/companies/<company_id>/income-statement")
def api_income_statement(company_id: str):
    loaded = _diu_and_coa()
    if not loaded:
        return jsonify({"error": "no reference workbook is set up yet"}), 404
    entity = _entities_by_slug().get(company_id)
    if not entity:
        return jsonify({"error": f"no company {company_id!r}"}), 404
    diu, coa = loaded
    return jsonify(report_statements.income_statement(diu, coa, legal_entity=entity))


@app.get("/api/companies/<company_id>/cash-flow")
def api_cash_flow(company_id: str):
    """Deliberately honest rather than invented: the data has a cash/non-cash flag
    (`cash_leg_transtype`) and a transaction classification, but nothing that maps to
    operating, investing and financing activities. Returning fabricated numbers here is
    exactly the failure this whole product argues against -- see docs/analyst-flags.md.
    """
    entity = _entities_by_slug().get(company_id)
    if not entity:
        return jsonify({"error": f"no company {company_id!r}"}), 404
    return jsonify(
        {
            "legal_entity": entity,
            "available": False,
            "reason": (
                "This data has a cash/non-cash flag and a transaction classification, "
                "but nothing that maps to operating, investing and financing activities. "
                "Building this needs a real mapping decision, not a rollup -- see "
                "docs/analyst-flags.md."
            ),
        }
    )


def _public_gl_migration_flag(flag) -> dict:
    """Dataset 02's flags carry their own kind of source (`legal_entity`, `sheet`,
    `deal_name` ...) -- nothing like a bank statement's `pdf`/`page`/`row_id`, so
    `_safe_source`'s whitelist would silently drop all of it. Pass `source` through
    whole; there is no server filesystem path in it to strip in the first place.
    """
    return {
        "flag_id": flag.flag_id,
        "check": flag.check,
        "label": labels.check_label(flag.check),
        "severity": flag.severity,
        "severity_label": labels.severity_label(flag.severity),
        "message": flag.message,
        "source": flag.source,
        "expected": flag.expected,
        "actual": flag.actual,
    }


_GL_MIGRATION_CACHE: dict[tuple, list[dict]] = {}


def _gl_migration_cache_key(space: gl_workspace.GLWorkspace) -> tuple:
    """Resolved path + mtime for each file, so a fresh upload invalidates the cache
    automatically -- no explicit "clear" call needed anywhere the files can change."""
    return (
        str(space.gl.resolve()), space.gl.stat().st_mtime,
        str(space.output.resolve()), space.output.stat().st_mtime,
    )


def run_gl_migration(space: gl_workspace.GLWorkspace | None = None) -> list[dict]:
    """The public flags for whichever GL/loader pair is current, computed once per
    distinct pair of files and cached after that -- the 34,000-row source GL takes a few
    seconds to read."""
    space = space or gl_workspace.current()
    key = _gl_migration_cache_key(space)
    if key not in _GL_MIGRATION_CACHE:
        flags = gl_migration.analyze(space.gl, space.output)
        _GL_MIGRATION_CACHE[key] = [_public_gl_migration_flag(flag) for flag in flags]
    return _GL_MIGRATION_CACHE[key]


@app.get("/api/gl-migration/flags")
def api_gl_migration_flags():
    """Dataset 02 (investor-level GL -> loader), analyzed independently of the bank
    statement pipeline above -- a different dataset, a different shape of data (no
    per-transaction `Row`), so it gets its own endpoint rather than being forced through
    `/api/review`. See `src/gl_migration/analyze.py`.

    Reads whatever `gl_workspace.current()` says is current: an uploaded GL and/or loader
    workbook from `/gl-upload` if one was saved, the bundled sample otherwise -- the same
    "uploaded wins, bundled is the fallback" the bank-statement side uses.
    """
    try:
        flags = run_gl_migration()
    except FileNotFoundError as error:
        return jsonify({"error": f"dataset 02 not found: {error}"}), 404
    by_check: dict[str, int] = {}
    for flag in flags:
        by_check[flag["check"]] = by_check.get(flag["check"], 0) + 1
    return jsonify({"flags_found": len(flags), "by_check": by_check, "flags": flags})


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


@app.get("/gl-upload")
def gl_upload_form():
    space = gl_workspace.current()
    try:
        flags = run_gl_migration(space)
        error = None
    except FileNotFoundError as failure:
        flags, error = [], request.args.get("error") or str(failure)
    by_check: dict[str, int] = {}
    for flag in flags:
        by_check[flag["check"]] = by_check.get(flag["check"], 0) + 1
    return render_template(
        "gl_upload.html",
        space=space,
        flags_found=len(flags),
        by_check=[(labels.check_label(check), count) for check, count in sorted(by_check.items())],
        error=error or request.args.get("error"),
    )


@app.post("/gl-upload")
def gl_upload():
    """Take this tranche's GL and/or loader workbook. Either alone is a real case --
    a new GL against a loader/mapping that has not changed, or a corrected loader against
    a GL already uploaded -- so both are optional, but at least one has to be present."""
    gl_file = request.files.get("gl")
    output_file = request.files.get("loader")
    has_gl = bool(gl_file and gl_file.filename)
    has_output = bool(output_file and output_file.filename)

    if not has_gl and not has_output:
        return redirect(url_for("gl_upload_form", error="Choose at least one workbook to upload."))
    for label_text, upload_file, present in (
        ("GL workbook", gl_file, has_gl),
        ("loader workbook", output_file, has_output),
    ):
        if present and not upload_file.filename.lower().endswith((".xlsx", ".xlsm")):
            return redirect(url_for(
                "gl_upload_form", error=f"The {label_text} has to be an Excel file (.xlsx)."
            ))

    gl_workspace.save(gl_file if has_gl else None, output_file if has_output else None)
    try:
        run_gl_migration()
    except FileNotFoundError as failure:
        return redirect(url_for("gl_upload_form", error=str(failure)))
    return redirect(url_for("gl_upload_form"))


@app.post("/reset")
def reset():
    save_decisions({})
    save_flag_decisions({})
    return redirect(url_for("index"))
