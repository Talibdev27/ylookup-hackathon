"""The Marker client, without a real Marker service or network call.

`requests.post` is monkeypatched directly rather than via a pytest fixture, because
every test file in this repo also has to run standalone (`python tests/test_x.py`) for
`run-tests.sh`, and pytest fixtures are not available outside pytest.

Run:  python -m pytest tests/ -q      (or: python tests/test_marker_client.py)
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from src.extraction import marker_client


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


def _with_env(url: str | None, fn):
    """Run `fn` with MARKER_SERVICE_URL set to `url` (or unset), then restore it."""
    key = marker_client.ENV_VAR
    original = os.environ.get(key)
    try:
        if url is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = url
        return fn()
    finally:
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original


def _with_fake_post(fake_post, fn):
    original = requests.post
    requests.post = fake_post
    try:
        return fn()
    finally:
        requests.post = original


def _tmp_pdf() -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    handle.write(b"%PDF-1.4 not a real pdf, just bytes to send")
    handle.close()
    return Path(handle.name)


def test_unavailable_when_not_configured() -> None:
    pdf = _tmp_pdf()
    try:
        assert not _with_env(None, marker_client.available)

        def call():
            marker_client.extract(pdf)

        raised = False
        try:
            _with_env(None, call)
        except marker_client.MarkerUnavailable:
            raised = True
        assert raised, "expected MarkerUnavailable when MARKER_SERVICE_URL is unset"
    finally:
        pdf.unlink(missing_ok=True)


def test_extract_returns_markdown_on_success() -> None:
    pdf = _tmp_pdf()

    def fake_post(url, files=None, timeout=None):
        assert url == "http://example.test/extract"
        assert "file" in files
        return _FakeResponse(200, {"markdown": "# Balance Sheet\n\nCash: 1,000"})

    try:
        result = _with_env(
            "http://example.test",
            lambda: _with_fake_post(fake_post, lambda: marker_client.extract(pdf)),
        )
        assert result == "# Balance Sheet\n\nCash: 1,000"
    finally:
        pdf.unlink(missing_ok=True)


def test_extract_raises_marker_error_on_bad_status() -> None:
    pdf = _tmp_pdf()

    def fake_post(url, files=None, timeout=None):
        return _FakeResponse(500, text="marker could not convert this file")

    try:
        raised = False
        try:
            _with_env(
                "http://example.test",
                lambda: _with_fake_post(fake_post, lambda: marker_client.extract(pdf)),
            )
        except marker_client.MarkerError:
            raised = True
        assert raised, "expected MarkerError on a non-200 response"
    finally:
        pdf.unlink(missing_ok=True)


def test_extract_raises_marker_error_on_network_failure() -> None:
    pdf = _tmp_pdf()

    def fake_post(url, files=None, timeout=None):
        raise requests.ConnectionError("connection refused")

    try:
        raised = False
        try:
            _with_env(
                "http://example.test",
                lambda: _with_fake_post(fake_post, lambda: marker_client.extract(pdf)),
            )
        except marker_client.MarkerError:
            raised = True
        assert raised, "expected MarkerError when the service is unreachable"
    finally:
        pdf.unlink(missing_ok=True)


if __name__ == "__main__":
    test_unavailable_when_not_configured()
    test_extract_returns_markdown_on_success()
    test_extract_raises_marker_error_on_bad_status()
    test_extract_raises_marker_error_on_network_failure()
    print("all marker client checks pass")
