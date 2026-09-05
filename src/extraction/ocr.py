"""OCR via Tesseract, for a page with no text layer to read.

`pdf_text.py` reads a PDF's own text layer directly with `pdfplumber`, which is all
every document in this dataset needs -- they are digitally generated, not scanned, so
there is nothing to recognise. This module is the fallback for the day a scanned or
photographed document shows up: rasterise the page and read the pixels instead.

`pytesseract` itself is a thin, pure-Python wrapper -- the actual OCR engine is the
`tesseract` binary, a separate system install, not a pip package:

    macOS     brew install tesseract
    Debian    apt-get install tesseract-ocr
    Windows   https://github.com/UB-Mannheim/tesseract/wiki

`available()` checks for that binary at runtime, so a missing install degrades to "no
OCR happened" rather than a stack trace three calls deep -- see how `pdf_text.extract()`
uses it.
"""
from __future__ import annotations

import pytesseract

_RESOLUTION = 300  # dpi. Tesseract's own docs recommend 300 as the accuracy/speed floor.


def available() -> bool:
    """Whether the tesseract binary is actually installed and callable, not just whether
    the `pytesseract` package is importable -- those are two different things."""
    try:
        pytesseract.get_tesseract_version()
        return True
    except (pytesseract.TesseractNotFoundError, EnvironmentError):
        return False


def extract_page_image(page) -> str:
    """OCR one already-open `pdfplumber` page.

    Takes the `pdfplumber` `Page` object directly rather than a path and a page number,
    so a caller that already has the PDF open (as `pdf_text.extract()` does) does not
    reopen the file per page.
    """
    if not available():
        raise RuntimeError(
            "the tesseract binary is not installed or not on PATH -- "
            "see this module's docstring for how to install it"
        )
    image = page.to_image(resolution=_RESOLUTION).original
    return pytesseract.image_to_string(image)
