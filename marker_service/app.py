"""A thin HTTP wrapper around Marker, deployed separately from the main app.

Why this is its own service rather than a module in `src/`: Marker needs Python 3.10+
and PyTorch, plus several hundred MB of OCR model weights downloaded on first use. The
main app targets Python 3.9 and is deployed as a single lightweight worker on Render's
free tier, which cannot hold PyTorch and the model weights in memory at all. Keeping
this here means the main app's dependencies, deploy size and cold-start time are
completely unaffected by Marker's existence -- see `marker_service/README.md` for how
this gets deployed and `src/extraction/marker_client.py` for how the main app calls it.

The model dictionary is loaded once at process startup, not per request -- `create_model_dict()`
loads every model weight Marker needs, and doing that on every call would make each
request take as long as a cold start.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marker_service")

app = FastAPI(title="marker-service", version="1.0.0")

# A PDF larger than this is almost certainly not a single fund document, and Marker's
# per-page cost means a huge file could tie up the one worker for minutes.
MAX_UPLOAD_BYTES = 64 * 1024 * 1024

_converter = None  # populated once, on first use -- see _get_converter()


def _get_converter():
    """Build the PdfConverter once and reuse it. Imported lazily so importing this
    module (for a health check, or by a test) never requires torch to be installed."""
    global _converter
    if _converter is None:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        logger.info("loading marker models -- this happens once per process")
        _converter = PdfConverter(artifact_dict=create_model_dict())
        logger.info("marker models loaded")
    return _converter


@app.get("/health")
def health() -> dict:
    """Whether the service is up. Does not report whether models are loaded yet --
    the first real request pays that cost, deliberately, rather than blocking startup."""
    return {"status": "ok"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)) -> JSONResponse:
    """One PDF in, its Markdown text out.

    Accepts a multipart upload rather than Marker's own bundled `marker_server`, which
    takes a filepath already present on the server's filesystem -- no use to a caller on
    a different machine. This is the same `PdfConverter` / `text_from_rendered` call the
    Marker README's own Python quickstart uses, wrapped to take bytes over the network
    instead of a local path.
    """
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, f"expected a PDF, got content-type {file.content_type!r}")

    body = await file.read()
    if not body:
        raise HTTPException(400, "the uploaded file was empty")
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")

    from marker.output import text_from_rendered

    with tempfile.NamedTemporaryFile(suffix=".pdf") as staged:
        staged.write(body)
        staged.flush()
        try:
            rendered = _get_converter()(staged.name)
        except Exception:
            logger.exception("marker failed to convert %s", file.filename)
            raise HTTPException(500, "marker could not convert this file") from None

    text, _, images = text_from_rendered(rendered)
    return JSONResponse(
        {
            "filename": file.filename,
            "markdown": text,
            "image_count": len(images or {}),
        }
    )


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
