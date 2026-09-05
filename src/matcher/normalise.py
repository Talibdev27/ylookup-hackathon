"""Narrative normalisation.

The bank writes counterparty names truncated, in capitals, and wrapped across lines
mid-word with commas inserted at the wrap points:

    NI ABF I SCSP, PMT FRM NI ABF II SCSP TO NI ABF I, SCSP FOR PURCHASE 100PER OF ACC INT

Matching happens on the normalised form; evidence spans must point back into the raw
form, so `normalise` returns an index map alongside the text.
"""
from __future__ import annotations

import html
import re

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[,/;:()\[\]]+")
# Suffixes the master lists spell out but the bank truncates or drops.
_NOISE = {"SCSP", "SARL", "SA", "SCS", "LTD", "LIMITED", "GMBH", "BV", "UA", "PS", "AS"}


def normalise(raw: str) -> tuple[str, list[int]]:
    """Return (normalised_text, index_map) where index_map[i] is the offset in `raw`
    that produced normalised_text[i]. Use it to turn a match on the normalised form
    back into a highlight span on the original."""
    text = html.unescape(raw)
    out_chars: list[str] = []
    index_map: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        if _PUNCT.match(ch) or ch.isspace():
            if not prev_space:
                out_chars.append(" ")
                index_map.append(i)
                prev_space = True
            continue
        out_chars.append(ch.upper())
        index_map.append(i)
        prev_space = False
    normalised = "".join(out_chars).strip()
    # strip() may have removed a leading space; realign
    lead = len("".join(out_chars)) - len("".join(out_chars).lstrip())
    return normalised, index_map[lead : lead + len(normalised)]


def tokens(text: str, drop_noise: bool = True) -> list[str]:
    """Comparable tokens. Legal-form suffixes are dropped by default because the bank
    truncates them inconsistently and they carry almost no discriminating signal."""
    raw_tokens = [t for t in _WS.split(text.upper()) if t]
    if not drop_noise:
        return raw_tokens
    return [t for t in raw_tokens if t not in _NOISE and len(t) > 1]


def span_in_raw(index_map: list[int], start: int, end: int) -> tuple[int, int]:
    """Map a [start, end) span on the normalised text back to raw character offsets."""
    if not index_map or start >= len(index_map):
        return (0, 0)
    end = min(end, len(index_map))
    return (index_map[start], index_map[end - 1] + 1)
