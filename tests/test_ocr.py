"""Tesseract OCR. `available()` must work whether or not the binary is actually
installed; the real OCR check runs for real when it is, and says so and skips when it
is not, rather than failing a checkout that has not installed a system binary yet.

Run:  python -m pytest tests/ -q      (or: python tests/test_ocr.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction import ocr


def test_available_never_raises() -> None:
    assert ocr.available() in (True, False)


def test_reads_text_from_a_generated_image() -> None:
    if not ocr.available():
        print("tesseract binary not installed -- skipping the real OCR check")
        return

    from PIL import Image, ImageDraw, ImageFont
    import pytesseract

    image = Image.new("RGB", (600, 150), "white")
    font = ImageFont.load_default(size=48)
    ImageDraw.Draw(image).text((10, 40), "HELLO WORLD", fill="black", font=font)

    text = pytesseract.image_to_string(image).upper()
    assert "HELLO" in text and "WORLD" in text, f"tesseract read: {text!r}"


if __name__ == "__main__":
    test_available_never_raises()
    test_reads_text_from_a_generated_image()
    print("all ocr checks pass")
