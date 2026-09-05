"""`src/gl_migration/workspace.py`: uploaded wins, the bundled sample is the fallback,
checked independently per file -- the gap this closes is that `analyze()` always took
explicit paths but nothing ever passed anything except the bundled sample's hardcoded
ones. `/gl-upload` in `src/ui/app.py` is the caller; this tests the workspace logic on
its own, without going through Flask's multipart handling.

Run:  python -m pytest tests/test_gl_workspace.py -q      (or: python tests/test_gl_workspace.py)
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gl_migration import load, workspace


class _FakeUpload:
    """Stands in for Werkzeug's `FileStorage` -- workspace.save() only ever calls
    `.save(path)` on what it's given, so that's the only method a fake needs."""

    def __init__(self, content: bytes) -> None:
        self.content = content

    def save(self, path: str) -> None:
        Path(path).write_bytes(self.content)


def _reset() -> None:
    if workspace.WORKSPACE.exists():
        shutil.rmtree(workspace.WORKSPACE)


def test_nothing_uploaded_falls_back_to_the_bundled_sample() -> None:
    _reset()
    space = workspace.current()
    assert space.gl == load.SOURCE_GL
    assert space.output == load.OUTPUT_LOADER
    assert space.is_bundled and space.gl_is_bundled and space.output_is_bundled


def test_uploading_one_file_leaves_the_other_on_the_bundled_sample() -> None:
    """A new GL against a loader workbook that has not changed is a real case -- the two
    halves are independent, the same way dataset 01's workbook and statements are."""
    _reset()
    workspace.save(gl_file=_FakeUpload(b"fake gl bytes"), output_file=None)
    space = workspace.current()
    assert space.gl == workspace.WORKSPACE / "gl.xlsx"
    assert space.gl.read_bytes() == b"fake gl bytes"
    assert not space.gl_is_bundled
    assert space.output == load.OUTPUT_LOADER
    assert space.output_is_bundled
    assert not space.is_bundled
    _reset()


def test_uploading_both_files_replaces_both() -> None:
    _reset()
    workspace.save(
        gl_file=_FakeUpload(b"gl v1"),
        output_file=_FakeUpload(b"loader v1"),
    )
    space = workspace.current()
    assert space.gl.read_bytes() == b"gl v1"
    assert space.output.read_bytes() == b"loader v1"
    assert not space.is_bundled

    # A second upload of just one file overwrites only that one.
    workspace.save(gl_file=_FakeUpload(b"gl v2"), output_file=None)
    space = workspace.current()
    assert space.gl.read_bytes() == b"gl v2"
    assert space.output.read_bytes() == b"loader v1", "an upload of one file must not touch the other"
    _reset()


def test_gl_upload_route_runs_the_real_checks_against_uploaded_files() -> None:
    """End to end through Flask: uploading the bundled sample's own two workbooks through
    `/gl-upload` should produce the identical 220 flags `analyze()` finds directly --
    proving the route, the saved files and the cache-invalidation-by-mtime all actually
    connect, not just that `workspace.py` behaves correctly in isolation."""
    _reset()
    from src.ui import app as ui

    client = ui.app.test_client()
    try:
        no_files = client.post("/gl-upload")
        assert no_files.status_code == 302
        assert "error=" in no_files.headers["Location"]

        with open(load.SOURCE_GL, "rb") as gl_fh, open(load.OUTPUT_LOADER, "rb") as out_fh:
            response = client.post(
                "/gl-upload",
                data={"gl": (gl_fh, "gl.xlsx"), "loader": (out_fh, "loader.xlsx")},
                content_type="multipart/form-data",
            )
        assert response.status_code == 302
        assert "error" not in response.headers["Location"]

        space = workspace.current()
        assert not space.is_bundled

        page = client.get("/gl-upload")
        assert page.status_code == 200 and b"220" in page.data

        api = client.get("/api/gl-migration/flags")
        assert api.status_code == 200
        assert api.get_json()["flags_found"] == 4 + 16 + 198 + 2
    finally:
        _reset()


if __name__ == "__main__":
    test_nothing_uploaded_falls_back_to_the_bundled_sample()
    test_uploading_one_file_leaves_the_other_on_the_bundled_sample()
    test_uploading_both_files_replaces_both()
    test_gl_upload_route_runs_the_real_checks_against_uploaded_files()
    print("all gl_workspace checks pass")
