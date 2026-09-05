"""Call the Marker service, if one is configured.

Marker gives better extraction than `pdf_text.py`'s `pdfplumber` on complex, multi-column
or image-heavy documents, but it needs Python 3.10+ and PyTorch, which this app's Python
3.9 target and single lightweight Render worker cannot carry -- see
`marker_service/README.md` for why that lives as a separate deployment instead of a
module in here.

This module is the only thing in the main app that knows the service exists. It adds one
dependency, `requests`, and nothing else: no torch, no version bump, no change to how the
app runs when `MARKER_SERVICE_URL` is unset, which is the common case for local dev and
for anyone who has not deployed the service.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

ENV_VAR = "MARKER_SERVICE_URL"
DEFAULT_TIMEOUT = 300.0  # a slow image-heavy PDF on CPU can take minutes, not seconds


class MarkerUnavailable(RuntimeError):
    """No Marker service is configured for this run. Not an error in itself -- a caller
    that wants Marker as an enhancement rather than a requirement should catch this and
    fall back to `pdf_text.extract()`."""


class MarkerError(RuntimeError):
    """A service is configured but the call failed -- unreachable, timed out, or it
    rejected or could not process the file. Kept apart from `MarkerUnavailable` because
    the two call for different responses: one is "not set up", the other is "set up and
    broken"."""


def configured_url() -> str | None:
    return os.environ.get(ENV_VAR) or None


def available() -> bool:
    return configured_url() is not None


def extract(pdf_path: Path, *, timeout: float = DEFAULT_TIMEOUT) -> str:
    """The Markdown text Marker reads out of `pdf_path`.

    Raises `MarkerUnavailable` if `MARKER_SERVICE_URL` is not set, and `MarkerError` for
    everything else that can go wrong -- this function does not decide whether a caller
    should fall back to `pdf_text.extract()` on failure, only reports which of the two
    situations occurred.
    """
    url = configured_url()
    if not url:
        raise MarkerUnavailable(f"{ENV_VAR} is not set -- no Marker service configured")

    try:
        with pdf_path.open("rb") as handle:
            response = requests.post(
                f"{url.rstrip('/')}/extract",
                files={"file": (pdf_path.name, handle, "application/pdf")},
                timeout=timeout,
            )
    except requests.RequestException as error:
        raise MarkerError(f"could not reach the Marker service at {url}: {error}") from error

    if response.status_code != 200:
        raise MarkerError(
            f"Marker service returned {response.status_code} for {pdf_path.name}: "
            f"{response.text[:300]}"
        )

    payload = response.json()
    markdown = payload.get("markdown")
    if not markdown:
        raise MarkerError(f"Marker service returned no markdown for {pdf_path.name}")
    return markdown
