"""Put a PDF or a workbook into the store, and read it back.

Version control here means one specific thing: the same filename uploaded twice with the
same bytes is a no-op, and uploaded twice with different bytes gets a new version number
rather than overwriting the old one. Content is compared by hash, not filename alone --
so "did this change" is a real answer, not a guess based on when it arrived.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection

from src.extraction import pdf_text
from src.spine.xlsx import Workbook


@dataclass(frozen=True)
class IngestResult:
    document_id: int
    version: int
    changed: bool  # False when this exact content was already the latest version


def _content_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _latest(conn: Connection, filename: str, kind: str) -> tuple[int, int, str] | None:
    """(id, version, content_hash) of the newest version on file for this filename and
    kind, or None if it has never been uploaded."""
    row = conn.execute(
        "SELECT id, version, content_hash FROM documents "
        "WHERE filename = ? AND kind = ? ORDER BY version DESC LIMIT 1",
        (filename, kind),
    ).fetchone()
    return tuple(row) if row else None


def ingest_pdf(conn: Connection, path: Path) -> IngestResult:
    """Extract `path` with `pdf_text.extract()` and store every page. A second upload of
    unchanged bytes touches nothing and returns the existing version."""
    raw = path.read_bytes()
    content_hash = _content_hash(raw)

    latest = _latest(conn, path.name, "pdf")
    if latest and latest[2] == content_hash:
        return IngestResult(document_id=latest[0], version=latest[1], changed=False)

    version = latest[1] + 1 if latest else 1
    document = pdf_text.extract(path)

    cursor = conn.execute(
        "INSERT INTO documents (filename, kind, content_hash, version, uploaded_at) "
        "VALUES (?, 'pdf', ?, ?, ?)",
        (path.name, content_hash, version, datetime.now(timezone.utc).isoformat()),
    )
    document_id = cursor.lastrowid
    for page in document.pages:
        conn.execute(
            "INSERT INTO pdf_pages (document_id, page_number, text, tables, used_ocr) "
            "VALUES (?, ?, ?, ?, ?)",
            (document_id, page.number, page.text, json.dumps(page.tables), int(page.ocr)),
        )
    conn.commit()
    return IngestResult(document_id=document_id, version=version, changed=True)


def ingest_workbook(conn: Connection, path: Path) -> IngestResult:
    """Read every sheet of `path` with the same `src/spine/xlsx.Workbook` reader the
    matcher uses, and store every row. Same change-detection rule as `ingest_pdf`."""
    raw = path.read_bytes()
    content_hash = _content_hash(raw)

    latest = _latest(conn, path.name, "workbook")
    if latest and latest[2] == content_hash:
        return IngestResult(document_id=latest[0], version=latest[1], changed=False)

    version = latest[1] + 1 if latest else 1
    book = Workbook(str(path))

    cursor = conn.execute(
        "INSERT INTO documents (filename, kind, content_hash, version, uploaded_at) "
        "VALUES (?, 'workbook', ?, ?, ?)",
        (path.name, content_hash, version, datetime.now(timezone.utc).isoformat()),
    )
    document_id = cursor.lastrowid
    # The reference workbook runs to several thousand rows across its sheets --
    # `executemany` in one transaction rather than one `execute()` per row, so a first
    # real upload does not add a noticeable delay on top of the pipeline it triggers.
    values = [
        (document_id, sheet_name, index, json.dumps(row))
        for sheet_name in book.sheet_names()
        for index, row in enumerate(book.records(sheet_name))
    ]
    conn.executemany(
        "INSERT INTO workbook_rows (document_id, sheet_name, row_index, row_data) "
        "VALUES (?, ?, ?, ?)",
        values,
    )
    conn.commit()
    return IngestResult(document_id=document_id, version=version, changed=True)


def record_flags(conn: Connection, flags: list) -> None:
    """Replace the whole `flags` table with `flags`.

    These are always fully recomputed from the current data on a run -- the same reason
    `data/rows.json` is overwritten rather than appended to -- so re-running against
    unchanged data should show the same flags, not the same flags twice.
    """
    conn.execute("DELETE FROM flags")
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        "INSERT INTO flags (check_name, severity, message, source, expected, actual, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                flag.check,
                flag.severity,
                flag.message,
                json.dumps(flag.source),
                json.dumps(flag.expected),
                json.dumps(flag.actual),
                now,
            )
            for flag in flags
        ],
    )
    conn.commit()


def read_flags(conn: Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT check_name, severity, message, source, expected, actual, created_at "
        "FROM flags ORDER BY id"
    ).fetchall()
    return [
        {
            "check": r[0],
            "severity": r[1],
            "message": r[2],
            "source": json.loads(r[3]),
            "expected": json.loads(r[4]),
            "actual": json.loads(r[5]),
            "created_at": r[6],
        }
        for r in rows
    ]


def history(conn: Connection, filename: str, kind: str) -> list[dict]:
    """Every version stored for this filename, oldest first -- the version history
    itself, independent of reading any version's actual content back."""
    rows = conn.execute(
        "SELECT id, version, content_hash, uploaded_at FROM documents "
        "WHERE filename = ? AND kind = ? ORDER BY version ASC",
        (filename, kind),
    ).fetchall()
    return [
        {"document_id": r[0], "version": r[1], "content_hash": r[2], "uploaded_at": r[3]}
        for r in rows
    ]


def pdf_pages(conn: Connection, document_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT page_number, text, tables, used_ocr FROM pdf_pages "
        "WHERE document_id = ? ORDER BY page_number",
        (document_id,),
    ).fetchall()
    return [
        {"page_number": r[0], "text": r[1], "tables": json.loads(r[2]), "used_ocr": bool(r[3])}
        for r in rows
    ]


def workbook_sheet(conn: Connection, document_id: int, sheet_name: str) -> list[dict]:
    rows = conn.execute(
        "SELECT row_data FROM workbook_rows "
        "WHERE document_id = ? AND sheet_name = ? ORDER BY row_index",
        (document_id, sheet_name),
    ).fetchall()
    return [json.loads(r[0]) for r in rows]
