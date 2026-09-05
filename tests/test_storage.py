"""The unified store, against a real statement PDF and the real reference workbook --
not fakes, because whether `pdf_text.extract()` and the `.xlsx` reader's own output
round-trips through SQLite correctly is exactly what would be wrong to assume.

Run:  python -m pytest tests/ -q      (or: python tests/test_storage.py)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.spine.build import STATEMENTS, WORKBOOK
from src.storage import db, store


def _fresh_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    return db.connect(Path(tmp.name))


def test_ingesting_a_real_statement_stores_every_page() -> None:
    one_statement = next(iter(sorted(STATEMENTS.glob("*.pdf"))))
    conn = _fresh_db()

    result = store.ingest_pdf(conn, one_statement)
    assert result.changed is True
    assert result.version == 1

    pages = store.pdf_pages(conn, result.document_id)
    assert len(pages) > 0
    assert "Statement details" in pages[0]["text"]


def test_reuploading_unchanged_bytes_does_not_create_a_new_version() -> None:
    one_statement = next(iter(sorted(STATEMENTS.glob("*.pdf"))))
    conn = _fresh_db()

    first = store.ingest_pdf(conn, one_statement)
    second = store.ingest_pdf(conn, one_statement)

    assert second.changed is False
    assert second.version == first.version == 1
    assert second.document_id == first.document_id
    versions = store.history(conn, one_statement.name, "pdf")
    assert len(versions) == 1


def test_reuploading_changed_bytes_creates_a_new_version_and_keeps_the_old_one() -> None:
    one_statement = next(iter(sorted(STATEMENTS.glob("*.pdf"))))
    conn = _fresh_db()

    first = store.ingest_pdf(conn, one_statement)
    with tempfile.TemporaryDirectory() as tmp:
        edited = Path(tmp) / one_statement.name
        edited.write_bytes(one_statement.read_bytes() + b"\n% trailing byte, different content")
        second = store.ingest_pdf(conn, edited)

    assert second.changed is True
    assert second.version == 2
    assert second.document_id != first.document_id

    versions = store.history(conn, one_statement.name, "pdf")
    assert [v["version"] for v in versions] == [1, 2]
    # The first version's pages are still there, not replaced.
    assert store.pdf_pages(conn, first.document_id)


def test_ingesting_the_real_reference_workbook_stores_every_sheet() -> None:
    conn = _fresh_db()

    result = store.ingest_workbook(conn, WORKBOOK)
    assert result.changed is True

    legal_entities = store.workbook_sheet(conn, result.document_id, "Legal Entity Master List")
    assert len(legal_entities) == 97  # verified count, see src/spine/build.py EXPECTED_ROWS
    assert "Legal Entity" in legal_entities[0]


if __name__ == "__main__":
    test_ingesting_a_real_statement_stores_every_page()
    test_reuploading_unchanged_bytes_does_not_create_a_new_version()
    test_reuploading_changed_bytes_creates_a_new_version_and_keeps_the_old_one()
    test_ingesting_the_real_reference_workbook_stores_every_sheet()
    print("all storage checks pass")
