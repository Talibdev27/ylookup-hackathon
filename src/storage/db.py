"""The unified store: every PDF and workbook upload, extracted once and kept -- with a
full version history rather than an overwrite.

One SQLite file, not a managed database service. `docs/TASK-hosting.md` already commits
this app to state living on disk, one instance, a persistent volume if the platform
offers one -- a `.sqlite` file fits that exactly as well as the `data/rows.json` and
`data/decisions.json` this app already writes. This adds structure to that state, not a
different deployment shape or a new kind of thing to host.

Two content tables, one per file type, both hanging off one `documents` table that
carries the identity and version history:

    documents      one row per upload *event* that actually changed something --
                   filename, kind, a content hash, a version number, when
    pdf_pages      page number, text, tables (as JSON), whether OCR produced the text
    workbook_rows  sheet name, row index, the row itself (as JSON)

Re-uploading a file whose bytes have not changed does not create a new version -- see
`store.py`'s hash check. Re-uploading a genuinely different file bumps the version and
keeps the old one queryable, rather than replacing it.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_PATH = Path("data/store.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('pdf', 'workbook')),
    content_hash TEXT NOT NULL,
    version INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pdf_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    page_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    tables TEXT NOT NULL,
    used_ocr INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS workbook_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    sheet_name TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    row_data TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename, kind);
CREATE INDEX IF NOT EXISTS idx_pdf_pages_document ON pdf_pages(document_id);
CREATE INDEX IF NOT EXISTS idx_workbook_rows_document ON workbook_rows(document_id);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open the store, creating the schema if this is a fresh file. `CREATE TABLE IF NOT
    EXISTS` makes this safe to call on every startup, not just the first one."""
    path = path or DEFAULT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn
