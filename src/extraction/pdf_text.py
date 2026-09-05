"""Any PDF -> page text and page tables, independent of what kind of document it is.

`src/spine/pdf.py` already parses one very specific layout: bank statements laid out as
one transaction table per page. This module is the generic primitive underneath it and
under every future document type -- balance sheets, income statements, cash flow
statements -- none of which share that layout, or with each other. Extract first, decide
what kind of document it is second: see `docs/ROADMAP.md`.

`to_json()` is the handoff point to anything that is not Python -- a Node frontend
included. No extra dependency for it: `json` is the standard library, and a PDF's text
and tables are already plain strings and lists once pdfplumber has read them.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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


def to_dict(document: ExtractedDocument) -> dict:
    """`document` as plain dicts and lists -- the only types `json.dumps` needs.

    `source` is the filename alone, not the full local path: whatever reads this JSON
    is not guaranteed to be on the same machine or filesystem layout this ran on.
    """
    return {
        "source": document.source.name,
        "pages": [asdict(page) for page in document.pages],
    }


def to_json(document: ExtractedDocument, destination: Path) -> Path:
    """Write `document` out as JSON. One call after `extract()` is the whole pipeline:
    PDF in, text and tables out, structured for whatever reads it next."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(to_dict(document), indent=2))
    return destination
