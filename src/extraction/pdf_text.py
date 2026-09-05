"""Any PDF -> page text and page tables, independent of what kind of document it is.

`src/spine/pdf.py` already parses one very specific layout: bank statements laid out as
one transaction table per page. This module is the generic primitive underneath it and
under every future document type -- balance sheets, income statements, cash flow
statements -- none of which share that layout, or with each other. Extract first, decide
what kind of document it is second: see `docs/TASK-extraction-agent.md`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pdfplumber

Table = list[list["str | None"]]


@dataclass
class Page:
    number: int
    text: str
    tables: list[Table]


@dataclass
class ExtractedDocument:
    source: Path
    pages: list[Page]

    @property
    def text(self) -> str:
        """Every page's text, concatenated. Enough to classify a document by keyword or
        pass to a model; not enough to pull figures from reliably -- read `page.tables`
        for that, the way `src/spine/pdf.py` does for statements."""
        return "\n".join(page.text for page in self.pages)


def extract(path: Path) -> ExtractedDocument:
    pages = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            pages.append(
                Page(
                    number=number,
                    text=page.extract_text() or "",
                    tables=page.extract_tables(),
                )
            )
    return ExtractedDocument(source=path, pages=pages)
