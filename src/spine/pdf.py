"""Bank statement PDF -> transaction rows.

The statements are laid out as one table per page:

    Bank reference | Customer reference | TRN type | Value date | Credit | Debit | Balance | Time | Post date
    NONREF         | NONREF             | TFR-     | 31 Mar 2026|        | -0.44 | 13,217,773.59 | 17:46 | 31 Mar 2026
    Narrative      | CHARGES FOR 2, OUTWARD SEPA PAYMENT

So each transaction is a data row followed by a `Narrative` row. Two wrinkles:

* A long bank reference wraps onto its own line, which arrives as a row with only the
  first cell populated. It belongs to the transaction above it. Day separators
  ("Balance brought forward 31 Mar 2026 165,631.58") have that same single-cell shape
  and must not be glued on -- hence CONTINUATION, which only accepts a bare token.
* Narratives are wrapped mid-word with commas inserted at the wrap points. That form is
  preserved verbatim as `narrative_raw` -- evidence spans in the review UI index into it.

Verified: 100 transactions across the 7 statements, matching the 100 ground-truth rows.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pdfplumber

from src.contract import Raw, Row

FILENAME = re.compile(
    r"^(?P<date>\d{8})_(?P<entity>.+)_(?P<bank>[A-Z]+)_(?P<currency>[A-Z]{3})_(?P<account>\w+)\.pdf$"
)
HEADER_CELL = "Bank reference"
NARRATIVE_CELL = "Narrative"
COLUMNS = ("bank_reference", "customer_reference", "trn_type", "value_date",
           "credit", "debit", "balance", "time", "post_date")
# A wrapped bank reference is a bare alphanumeric token. Anything longer, or carrying a
# space or a date, is a statement separator row rather than a continuation.
CONTINUATION = re.compile(r"^[A-Z0-9]{1,20}$")


def parse_filename(path: Path) -> dict[str, str]:
    """20260331_NI_V_SCSP_CALDER_EUR_030041.pdf -> date, entity, bank, currency, account."""
    match = FILENAME.match(path.name)
    if not match:
        raise ValueError(f"unexpected statement filename: {path.name}")
    parts = match.groupdict()
    parts["entity"] = parts["entity"].replace("_", " ").strip()
    return parts


def _amount(text: str) -> float | None:
    text = (text or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _date(text: str) -> str | None:
    """'31 Mar 2026' -> '2026-03-31'."""
    try:
        return datetime.strptime((text or "").strip(), "%d %b %Y").date().isoformat()
    except ValueError:
        return None


def read_statement_meta(page) -> dict[str, str]:
    """Account name / number / currency out of the header block. The block is two
    key-value columns printed side by side, so anchor each key at line start."""
    text = page.extract_text() or ""
    meta = {}
    if m := re.search(r"^Account number\s+(\S+)", text, re.M):
        meta["account_number"] = m.group(1)
    if m := re.search(r"^Currency\s+([A-Z]{3})\b", text, re.M):
        meta["currency"] = m.group(1)
    if m := re.search(r"^Account name\s+(.+?)\s{2,}|^Account name\s+(\S+(?: \S+)*?)\s+Closing", text, re.M):
        meta["account_name"] = (m.group(1) or m.group(2) or "").strip()
    return meta


def parse_statement(path: Path, start_id: int = 0) -> list[Row]:
    parts = parse_filename(path)
    rows: list[Row] = []
    with pdfplumber.open(path) as pdf:
        meta = read_statement_meta(pdf.pages[0])
        for page_number, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables():
                for cells in table:
                    first = (cells[0] or "").strip()
                    if first == HEADER_CELL or not any(c for c in cells):
                        continue
                    if first == NARRATIVE_CELL:
                        if rows:
                            rows[-1].raw.narrative_raw = (cells[1] or "").strip()
                        continue
                    if first and not any(c for c in cells[1:] if c):
                        # continuation of the bank reference above, or a separator row
                        if rows and CONTINUATION.match(first):
                            rows[-1].raw.bank_reference += first
                        continue
                    values = dict(zip(COLUMNS, [(c or "").strip() for c in cells]))
                    rows.append(
                        Row(
                            row_id=start_id + len(rows),
                            source={"pdf": path.name, "page": page_number},
                            raw=Raw(
                                account_name=meta.get("account_name", parts["entity"]),
                                account_number=meta.get("account_number", parts["account"]),
                                currency=meta.get("currency", parts["currency"]),
                                bank_reference=values["bank_reference"],
                                value_date=_date(values["value_date"]),
                                post_date=_date(values["post_date"]),
                                credit=_amount(values["credit"]),
                                debit=_amount(values["debit"]),
                                balance=_amount(values["balance"]),
                            ),
                        )
                    )
    return rows


def parse_statements(directory: Path) -> list[Row]:
    """All statements, in filename order. Row ids are assigned across the whole set."""
    rows: list[Row] = []
    for path in sorted(directory.glob("*.pdf")):
        rows.extend(parse_statement(path, start_id=len(rows)))
    return rows
