"""`POST /api/upload`: the JSON sibling of `/upload`, built for `truss/`'s dropzone -- a
fetch() from a different origin wants a status and a result back, not a 302 to a Jinja
page it would have to parse. `_process_statement_upload` in `src/ui/app.py` is the one
path both routes share; this pins the JSON contract on top of it.

`/upload`, `/gl-upload` and `/api/gl-migration/upload` are exercised manually against a
live server elsewhere (see the commit that added them) rather than here, since covering
every route with an automated multipart test is more machinery than three routes with an
identical shared implementation are worth. `/api/upload` gets one because it is the one
that mutates `data/workspace/` -- the workspace this whole app runs against outside
tests too -- so its backup/restore is worth writing once and keeping.

Run:  python -m pytest tests/test_upload_api.py -q      (or: python tests/test_upload_api.py)
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.spine import workspace


@contextmanager
def real_workspace_preserved():
    """`/api/upload` calls `workspace.save_workbook()` / `clear_statements()`, which
    permanently replace `data/workspace/` -- the same directory the demo and every other
    test's `workspace.current()` call reads outside this test. Move it aside and restore
    it, rather than leaving whatever the test uploaded as the new permanent state."""
    from src.ui import app as ui

    backup_dir = None
    if workspace.WORKSPACE.exists():
        backup_dir = Path(tempfile.mkdtemp()) / "workspace-backup"
        shutil.move(str(workspace.WORKSPACE), str(backup_dir))

    data_paths = (ui.ROWS, ui.DECISIONS, ui.FLAGS, ui.FLAG_DECISIONS)
    saved = {path: path.read_bytes() if path.exists() else None for path in data_paths}
    try:
        yield ui, ui.app.test_client()
    finally:
        if workspace.WORKSPACE.exists():
            shutil.rmtree(workspace.WORKSPACE)
        if backup_dir is not None:
            shutil.move(str(backup_dir), str(workspace.WORKSPACE))
        for path, content in saved.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)


def test_api_upload_rejects_an_empty_request() -> None:
    with real_workspace_preserved() as (_, client):
        response = client.post("/api/upload")
        assert response.status_code == 400
        assert response.get_json() == {"error": "Choose at least one bank statement to upload."}


def test_api_upload_rejects_a_non_pdf_statement() -> None:
    with real_workspace_preserved() as (_, client):
        response = client.post(
            "/api/upload",
            data={"statements": (io.BytesIO(b"not a pdf"), "not-a-statement.txt")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        assert "PDF" in response.get_json()["error"]


def test_api_upload_runs_the_real_pipeline_and_returns_its_result() -> None:
    """Uploading the bundled sample's own workbook and one real statement through
    `/api/upload` should produce the same shape of result `_process_statement_upload`
    always has: rows processed, which checks ran, how many findings -- proving the JSON
    route, not just the HTML one, actually drives the real pipeline."""
    bundled = workspace._bundled()
    assert bundled.workbook and bundled.statement_files, "bundled sample dataset not found"
    one_statement = bundled.statement_files[0]

    with real_workspace_preserved() as (ui, client):
        with open(bundled.workbook, "rb") as wb_fh, open(one_statement, "rb") as stmt_fh:
            response = client.post(
                "/api/upload",
                data={
                    "workbook": (wb_fh, "reference.xlsx"),
                    "statements": (stmt_fh, one_statement.name),
                },
                content_type="multipart/form-data",
            )
        assert response.status_code == 200, response.get_json()
        body = response.get_json()
        assert body["ok"] is True
        assert body["rows"] >= 1
        assert isinstance(body["checks_applied"], list) and body["checks_applied"]
        assert isinstance(body["flags_found"], int)

        # The workspace really was replaced -- one statement, not the bundled sample's set.
        space = workspace.current()
        assert space.statement_files == [workspace.WORKSPACE / "statements" / one_statement.name]


if __name__ == "__main__":
    test_api_upload_rejects_an_empty_request()
    test_api_upload_rejects_a_non_pdf_statement()
    test_api_upload_runs_the_real_pipeline_and_returns_its_result()
    print("all upload API checks pass")
