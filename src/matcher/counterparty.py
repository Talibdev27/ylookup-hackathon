"""Pull the counterparty out of the bank narrative and match it to a master list.

This is the hard stage and the reason the product exists. The human doing it by hand
filled 55 of 100 rows and matched only 48; the 52 they left blank are the opportunity.

Two steps, deliberately separate so each can be scored on its own:

*Extraction* -- the bank narrative is comma-separated fragments, wrapped mid-word at the
line breaks. The counterparty is one of those fragments: usually the first, sometimes the
last, and often truncated where the bank ran out of line:

    NI ABF II MIZARCO S.A R., PAYMENT FROM ... TO TO NI ABF II MIZARCO S.A R.L. PROJECT ...
    ^ truncated here                                ^ the full form is later in the text

*Matching* -- against the reference lists, in the order the Process sheet reviews them.
The two sides are spelled differently on purpose: the bank writes uppercase ASCII, the
master list writes `NI ABF II MizarCo S.à r.l.`, and vendors carry office suffixes
(`Trentbeck Audit - Lu`). So comparison happens on a folded form, never on raw text.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Fragments that are references rather than names: account numbers, IBANs, transaction
# ids, the bank's own instruction codes.
NOISE_WORDS = {
    "TFR", "SCT", "CHARGE", "WAIVED", "PMT", "FRM", "PAYMENT", "FROM", "TO", "FOR",
    "OBO", "ON", "BEHALF", "OF", "INTERNAL", "TRANSFER", "REF", "NONREF", "PROJECT",
    "ACQ", "PURCHASE", "PURCHAS", "SHARES", "SHARE", "LOAN", "PRINCIP", "PREMIUM",
    "ACCRUED", "INTEREST", "TOTAL", "COST", "REL", "IN", "INV", "SETTLEMENT",
}

# Suffixes a master list adds that the bank never writes.
SUFFIX = re.compile(r"\s*-\s*(NON-)?LU$|\s*-\s*[A-Z]{2,3}$", re.I)


def fold(text: str) -> str:
    """Comparable form: accents stripped, punctuation dropped, uppercased.

    `NI ABF II MizarCo S.à r.l.` and `NI ABF II MIZARCO S.A R.L.` both fold to
    `NI ABF II MIZARCO S A R L`, which is the only reason they can be compared at all.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^A-Za-z0-9]+", " ", ascii_only).upper().split())


# The bank prefixes some narratives with a line number: "1/NORDVIK INFRASTRUCTURE PARTNER".
LINE_PREFIX = re.compile(r"^\d+\s*/\s*")


def tidy(fragment: str) -> str:
    """Strip the bank's line-number prefix and trailing punctuation left by a line break."""
    return LINE_PREFIX.sub("", fragment).strip().strip(".,;:-").strip()


def _is_reference(fragment: str) -> bool:
    """True for fragments that are identifiers rather than names."""
    letters = sum(ch.isalpha() for ch in fragment)
    digits = sum(ch.isdigit() for ch in fragment)
    return digits > letters or letters < 3


def _name_score(fragment: str) -> int:
    """How much this fragment looks like somebody's name."""
    words = [w for w in fold(fragment).split() if len(w) > 1]
    meaningful = [w for w in words if w not in NOISE_WORDS and not w.isdigit()]
    return len(meaningful)


def extract(narrative: str) -> tuple[str, tuple[int, int]] | None:
    """The counterparty as the bank wrote it, with its span in the raw narrative.

    The span is what the review screen highlights, so it must index into the text the
    reviewer is actually looking at -- not a normalised copy of it.
    """
    if not narrative:
        return None
    best: tuple[int, str, int, int] | None = None
    cursor = 0
    for fragment in narrative.split(","):
        start = narrative.index(fragment, cursor)
        end = start + len(fragment)
        cursor = end
        stripped = tidy(fragment)
        if not stripped or _is_reference(stripped):
            continue
        score = _name_score(stripped)
        if score < 1:
            continue
        # The first qualifying fragment wins outright -- the bank leads with the
        # counterparty. Scoring only decides whether a fragment qualifies at all.
        offset = fragment.index(stripped)
        best = (score, stripped, start + offset, start + offset + len(stripped))
        break
    if best is None:
        return None
    _, text, start, end = best
    return text, (start, end)


def complete(fragment: str, narrative: str) -> str:
    """Recover a name the bank truncated, when a longer comma-fragment spells it out.

    Only whole fragments are considered, and this is a deliberate limit rather than an
    oversight. Two looser versions were measured against the 55 names the human pulled
    by hand:

      whole fragments only          37 / 55
      any word window               17 / 55   (over-extends: every longer window still
                                               starts with the fragment)
      word windows stopped at a
      noise word                     7 / 55   (worse again -- stops in the wrong places)

    So `NI ABF II MIZARCO S.A R.` stays truncated when its full form only appears
    mid-fragment. Three rows lose their completion; twenty rows keep a correct name.
    That trade is why the loose versions are not here.
    """
    fragment = tidy(fragment)
    folded = fold(fragment)
    if not folded:
        return fragment
    longest = fragment
    for candidate in re.split(r"[,;]", narrative):
        candidate = tidy(candidate)
        if len(candidate) > len(longest) and fold(candidate).startswith(folded):
            longest = candidate
    return longest


@dataclass
class Match:
    value: str
    confidence: float
    source_list: str


def _index(entries: list[str]) -> dict[str, str]:
    """Folded form -> the master list's own spelling, which is what gets written out."""
    return {fold(entry): entry for entry in entries if entry and entry.strip()}


CURRENCY_SUFFIX = re.compile(r"\s-\s([A-Z]{3})$")


def match(
    name: str, lists: list[tuple[str, list[str]]], currency: str | None = None
) -> list[Match]:
    """Best matches across the reference lists, in the priority the Process sheet uses:
    related party, then legal entity, then investor, then vendor.

    Earlier lists win ties -- a counterparty that is a related party is a related party,
    even when the same name also appears as a vendor.

    Several master entries differ only by a trailing currency: `NI GMF II Coöperatief
    U.A.` and `NI GMF II Coöperatief U.A. - USD` are the same counterparty held in two
    currencies. The bank narrative never says which, so the row's own currency decides.
    """
    target = fold(name)
    if not target:
        return []
    target_tokens = {t for t in target.split() if t not in NOISE_WORDS}
    found: list[Match] = []
    for rank, (list_name, entries) in enumerate(lists):
        penalty = rank * 0.02  # a nudge, so priority breaks ties without hiding a better match
        for folded, original in _index(entries).items():
            if folded == target:
                found.append(Match(original, round(0.98 - penalty, 2), list_name))
                continue
            trimmed = fold(SUFFIX.sub("", original))
            if trimmed and trimmed == target:
                found.append(Match(original, round(0.92 - penalty, 2), list_name))
                continue
            if folded.startswith(target) or target.startswith(folded):
                shorter, longer = sorted((len(folded), len(target)))
                found.append(Match(original, round(0.62 + 0.28 * shorter / longer - penalty, 2), list_name))
                continue
            tokens = {t for t in folded.split() if t not in NOISE_WORDS}
            if tokens and target_tokens and (tokens <= target_tokens or target_tokens <= tokens):
                overlap = len(tokens & target_tokens) / max(len(tokens), len(target_tokens))
                if overlap >= 0.6:
                    found.append(Match(original, round(0.55 + 0.3 * overlap - penalty, 2), list_name))
    if currency:
        for candidate in found:
            suffix = CURRENCY_SUFFIX.search(candidate.value)
            if not suffix:
                continue
            # A currency-tagged entry is the better answer when it is this row's currency,
            # and the wrong answer when it is not.
            shift = 0.16 if suffix.group(1) == currency.upper() else -0.20
            candidate.confidence = round(min(0.99, max(0.0, candidate.confidence + shift)), 2)
    found.sort(key=lambda m: (-m.confidence, len(m.value)))
    deduped: list[Match] = []
    seen: set[str] = set()
    for candidate in found:
        if candidate.value not in seen:
            seen.add(candidate.value)
            deduped.append(candidate)
    return deduped
