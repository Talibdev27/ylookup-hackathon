"""Minimal, dependency-free .xlsx reader.

Written this way on purpose: the workbook has three traps that a naive reader walks
straight into, and all three fail silently.

1. Blank cells are omitted from the sheet XML. Reading cells positionally shifts every
   later column left. Cells must be placed by their `r=` reference.
2. Text is stored with raw HTML entities: `Co&#246;peratief`, `S.&#224; r.l.`. Left
   escaped, every string match against a master list misses.
3. Dates are Excel serials (46112 == 2026-03-05), not strings.
"""
from __future__ import annotations

import html
import re
import zipfile
from datetime import date, timedelta

EXCEL_EPOCH = date(1899, 12, 30)  # not 1900-01-01: Excel's leap-year bug


def _col_index(ref: str) -> int:
    """'AC12' -> 28. Zero-based column index from a cell reference."""
    letters = re.match(r"([A-Z]+)", ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def serial_to_date(value: str | int | float) -> date | None:
    """Excel serial -> date. Returns None for anything that isn't a plausible serial."""
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return None
    if not 1 <= n < 100_000:
        return None
    return EXCEL_EPOCH + timedelta(days=n)


class Workbook:
    """Reads sheets by name. Note the workbook contains a sheet literally named 'DIU '
    with a trailing space -- `sheet_names()` returns names verbatim."""

    _CELL = re.compile(r"<c\b([^>]*)>(.*?)</c>|<c\b([^>]*)/>", re.S)
    _ROW = re.compile(r"<row\b.*?</row>", re.S)

    def __init__(self, path: str) -> None:
        self._zip = zipfile.ZipFile(path)
        book = self._zip.read("xl/workbook.xml").decode("utf8")
        rels: dict[str, str] = {}
        rel_xml = self._zip.read("xl/_rels/workbook.xml.rels").decode("utf8")
        for rel in re.findall(r"<Relationship\b[^>]*/>", rel_xml):
            rid = re.search(r'Id="([^"]+)"', rel)
            target = re.search(r'Target="([^"]+)"', rel)
            if rid and target:
                rels[rid.group(1)] = target.group(1).lstrip("/")
        # Sheet names are XML-escaped in workbook.xml: 'Deal &amp; Position Master List'.
        self._sheets = {
            html.unescape(name): rels[rid]
            for name, rid in re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="(rId\d+)"', book)
        }
        # Shared strings are optional; this workbook uses inline strings, others may not.
        self._shared: list[str] = []
        if "xl/sharedStrings.xml" in self._zip.namelist():
            blob = self._zip.read("xl/sharedStrings.xml").decode("utf8")
            self._shared = [
                html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)))
                for si in re.findall(r"<si>(.*?)</si>", blob, re.S)
            ]

    def sheet_names(self) -> list[str]:
        return list(self._sheets)

    def _cell_value(self, attrs: str, inner: str) -> str:
        texts = re.findall(r"<t[^>]*>(.*?)</t>", inner, re.S)
        if texts:
            return html.unescape("".join(texts))
        match = re.search(r"<v>(.*?)</v>", inner, re.S)
        if not match:
            return ""
        value = match.group(1)
        if 't="s"' in attrs and value.isdigit() and int(value) < len(self._shared):
            return self._shared[int(value)]
        return html.unescape(value)

    def rows(self, sheet: str) -> list[list[str]]:
        """All rows as ragged-free lists, blank cells preserved as empty strings."""
        xml = self._zip.read(self._sheets[sheet]).decode("utf8")
        parsed: list[dict[int, str]] = []
        width = 0
        for row_xml in self._ROW.findall(xml):
            cells: dict[int, str] = {}
            for match in self._CELL.finditer(row_xml):
                attrs = match.group(1) or match.group(3) or ""
                inner = match.group(2) or ""
                ref = re.search(r'r="([A-Z]+\d+)"', attrs)
                if not ref:
                    continue
                cells[_col_index(ref.group(1))] = self._cell_value(attrs, inner)
            parsed.append(cells)
            width = max(width, max(cells, default=-1) + 1)
        return [[cells.get(i, "") for i in range(width)] for cells in parsed]

    def records(self, sheet: str, header_row: int = 0) -> list[dict[str, str]]:
        """Rows as dicts keyed by header, skipping entirely-blank rows."""
        rows = self.rows(sheet)
        if not rows:
            return []
        header = rows[header_row]
        out = []
        for row in rows[header_row + 1 :]:
            if not any(cell.strip() for cell in row):
                continue
            out.append({name: row[i] for i, name in enumerate(header) if name})
        return out
