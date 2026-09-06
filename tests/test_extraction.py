"""The extraction primitives, checked against a real statement PDF -- not a mock, because
a mock PDF cannot tell us pdfplumber's table layout assumptions still hold.

Run:  python -m pytest tests/ -q      (or: python tests/test_extraction.py)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction import ocr, pdf_text
from src.spine.build import STATEMENTS


def test_extract_reads_every_page_of_a_real_statement() -> None:
    one_statement = next(iter(sorted(STATEMENTS.glob("*.pdf"))))
    document = pdf_text.extract(one_statement)

    assert document.pages, "expected at least one page"
    assert "Statement details" in document.text
    # Every page of a bank statement carries its transaction table.
    assert all(page.tables for page in document.pages)


def test_to_json_round_trips_a_real_statement() -> None:
    one_statement = next(iter(sorted(STATEMENTS.glob("*.pdf"))))
    document = pdf_text.extract(one_statement)

    with tempfile.TemporaryDirectory() as tmp:
        destination = Path(tmp) / "extracted.json"
        pdf_text.to_json(document, destination)

        loaded = json.loads(destination.read_text())
        assert loaded["source"] == one_statement.name
        assert len(loaded["pages"]) == len(document.pages)
        assert loaded["pages"][0]["text"] == document.pages[0].text
        assert loaded["pages"][0]["tables"] == document.pages[0].tables


class _FakePage:
    """The two `pdfplumber` Page methods `extract()` actually calls."""

    def __init__(self, text: str):
        self._text = text

    def extract_text(self) -> str:
        return self._text

    def extract_tables(self) -> list:
        return []

    def to_image(self, resolution=None):
        class _Image:
            original = "not a real image, the fake OCR call below never looks at it"

        return _Image()


class _FakePDF:
    def __init__(self, pages: list[_FakePage]):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _with_fake_pdf(pages: list[_FakePage], fn):
    """Run `fn` with `pdfplumber.open` (as `pdf_text` calls it) swapped for a fake PDF --
    no real file needed, since what is under test is the OCR-fallback branching, not
    pdfplumber's own PDF reading, which the tests above already cover against real files.
    """
    original = pdf_text.pdfplumber.open
    pdf_text.pdfplumber.open = lambda path: _FakePDF(pages)
    try:
        return fn()
    finally:
        pdf_text.pdfplumber.open = original


def _with_ocr_stub(is_available: bool, reads_as: str, fn):
    original_available = ocr.available
    original_extract = ocr.extract_page_image
    ocr.available = lambda: is_available
    ocr.extract_page_image = lambda page: reads_as
    try:
        return fn()
    finally:
        ocr.available = original_available
        ocr.extract_page_image = original_extract


def test_ocr_fallback_fires_on_an_empty_text_layer_when_available() -> None:
    result = _with_fake_pdf(
        [_FakePage(text="")],
        lambda: _with_ocr_stub(
            True, "OCR READ THIS", lambda: pdf_text.extract(Path("fake.pdf"))
        ),
    )
    assert result.pages[0].text == "OCR READ THIS"
    assert result.pages[0].ocr is True


def test_ocr_fallback_is_skipped_when_tesseract_is_not_available() -> None:
    """An empty page stays empty rather than raising, when there is no OCR to fall back
    to -- today's normal case, since the tesseract binary is not installed everywhere."""
    result = _with_fake_pdf(
        [_FakePage(text="")],
        lambda: _with_ocr_stub(
            False, "should never be read", lambda: pdf_text.extract(Path("fake.pdf"))
        ),
    )
    assert result.pages[0].text == ""
    assert result.pages[0].ocr is False


def test_ocr_fallback_never_fires_when_the_text_layer_already_has_text() -> None:
    result = _with_fake_pdf(
        [_FakePage(text="already have this from the PDF itself")],
        lambda: _with_ocr_stub(
            True, "should never be read", lambda: pdf_text.extract(Path("fake.pdf"))
        ),
    )
    assert result.pages[0].text == "already have this from the PDF itself"
    assert result.pages[0].ocr is False


def test_ocr_fallback_can_be_turned_off() -> None:
    result = _with_fake_pdf(
        [_FakePage(text="")],
        lambda: _with_ocr_stub(
            True,
            "should never be read",
            lambda: pdf_text.extract(Path("fake.pdf"), ocr_fallback=False),
        ),
    )
    assert result.pages[0].text == ""
    assert result.pages[0].ocr is False


def test_a_missing_wrapper_package_degrades_like_a_missing_binary() -> None:
    """OCR is a fallback this dataset never reaches, and `pdf_text` imports `ocr`
    unconditionally, so an unguarded `import pytesseract` puts the whole review queue
    behind a pip install. The package and the binary are separate installs and either can
    be absent on its own; both have to degrade the same way."""
    import importlib

    saved = ocr.pytesseract
    ocr.pytesseract = None
    try:
        assert ocr.available() is False, "no wrapper means OCR cannot run"
        try:
            ocr.extract_page_image(None)
        except RuntimeError as refusal:
            assert "pytesseract package" in str(refusal), "say which half is missing"
        else:
            raise AssertionError("asking for OCR without the wrapper must refuse")
    finally:
        ocr.pytesseract = saved

    # And the app still imports, which is the failure this guards against.
    assert importlib.import_module("src.ui.app")


if __name__ == "__main__":
    test_extract_reads_every_page_of_a_real_statement()
    test_to_json_round_trips_a_real_statement()
    test_ocr_fallback_fires_on_an_empty_text_layer_when_available()
    test_ocr_fallback_is_skipped_when_tesseract_is_not_available()
    test_ocr_fallback_never_fires_when_the_text_layer_already_has_text()
    test_ocr_fallback_can_be_turned_off()
    print("all extraction checks pass")
