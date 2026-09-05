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
    """Strip the bank's line-number prefix and the punctuation a line break left behind.

    A trailing full stop survives, because it is usually part of the name rather than
    punctuation around it: the bank writes `NI V KALVIK TOPCO LTD.` and
    `NI GMF II COOPERATIEF U.A.`, where the stop closes the abbreviation. The human doing
    this by hand transcribes whichever form the bank wrote -- the same counterparty is
    recorded `... U.A.` on one row and `... U.A` on another, following the statement each
    time -- so removing it loses information rather than tidying it away.

    A run of stops is the abbreviation's own plus the sentence's, and collapses to one.
    Nothing downstream is affected either way: `fold` drops punctuation before comparing.
    """
    text = LINE_PREFIX.sub("", fragment).strip().strip(",;:-").strip()
    text = text.lstrip(".").strip()
    return re.sub(r"\.{2,}$", ".", text)


# Legal forms, as the token that closes a company's name. Written without their dots and
# accents, which is how `_looks_like_legal_form` compares them.
LEGAL_FORM_TOKENS = {
    "A/S", "K/S", "P/S", "APS", "SCSP", "SCS", "SCA", "LTD", "LIMITED", "GMBH", "INC",
    "LLC", "BV", "NV", "SARL", "SRL", "RL", "SA", "AB", "AS", "OY", "PLC", "CV", "LP",
    "UA", "GP",
}


def _looks_like_legal_form(word: str) -> bool:
    decomposed = unicodedata.normalize("NFKD", word)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return ascii_only.replace(".", "").replace(",", "").upper() in LEGAL_FORM_TOKENS


def drop_address(name: str) -> str:
    """Cut the street address the bank prints after a counterparty's name.

    `COVBURY ENERGI A/S FENNSTEAD 41` is one company and one address run together with
    nothing between them. A company's name closes at its legal form, so anything after
    that belongs to the address -- but only when it carries a house number, because
    `NI ABF II MIZARCO S.A R.L.` also continues past a legal form and there the
    continuation is the rest of the name.
    """
    words = name.split()
    for index, word in enumerate(words[:-1]):
        if not _looks_like_legal_form(word):
            continue
        rest = words[index + 1 :]
        if any(ch.isdigit() for word in rest for ch in word):
            return " ".join(words[: index + 1])
    return name


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
        stripped = drop_address(stripped)
        best = (score, stripped, start + offset, start + offset + len(stripped))
        break
    if best is None:
        return None
    _, text, start, end = best
    return text, (start, end)


def _read_name(text: str) -> str:
    """Read a name off the front of `text` and stop where the name stops.

    The bank runs straight from the counterparty into why it paid them --
    `NI RANFJORD II SCSP (EUR). PROJECT, RANFJORD II.` -- with no punctuation to separate
    the two. A name ends at the first word that belongs to the sentence rather than to
    the company: one of the bank's own instruction words, or a parenthesis, which is
    where it puts the currency and the security type.
    """
    words: list[str] = []
    for word in text.split():
        if word.startswith("(") or fold(word) in NOISE_WORDS:
            break
        words.append(word)
    return drop_address(tidy(" ".join(words)))


def complete(fragment: str, narrative: str) -> str:
    """Recover a name the bank truncated, when a longer comma-fragment spells it out.

    Whole fragments are tried first, then the middle of a fragment. The second pass used
    to be absent, and its absence was deliberate -- two unguarded versions were measured
    against the 55 names the human pulled by hand and both lost badly:

      whole fragments only          37 / 55
      any word window               17 / 55   (over-extends: every longer window still
                                               starts with the fragment)
      word windows stopped at a
      noise word                     7 / 55   (worse again -- stops in the wrong places)

    What makes the second pass safe now is two guards those versions did not have. A
    completion stops where the name stops rather than at the next comma (`_read_name`),
    and it has to add name rather than punctuation, so a later mention that folds
    identically to the fragment is not mistaken for a fuller spelling of it. With both,
    the middle-of-fragment pass rescues `NI ABF II MIZARCO S.A R.L.` and costs nothing.
    Remove either guard and the numbers above come straight back.
    """
    fragment = tidy(fragment)
    folded = fold(fragment)
    if not folded:
        return fragment
    longest = fragment
    for candidate in re.split(r"[,;]", narrative):
        # Compare what is left once the reason for the payment is dropped, so a later
        # mention of the same name followed by `PROJECT IAPETUS` is not mistaken for a
        # longer spelling of it.
        candidate = drop_address(strip_clause(candidate))
        if not fold(candidate).startswith(folded) or len(candidate) <= len(longest):
            continue
        # A completion has to add name, not punctuation. The bank writes this counterparty
        # `... U.A` on one row and `... U.A.` on the next; neither is more complete than
        # the other, and swapping one for the other is churn dressed up as a fix.
        if fold(candidate) == folded:
            continue
        longest = candidate
    if longest != fragment:
        return longest

    # The full spelling can sit inside a fragment rather than starting one:
    #
    #   NI ABF II MIZARCO S.A R., PAYMENT FROM ..., TO TO NI ABF II MIZARCO S.A R.L. PROJECT
    #   ^ the bank ran out of line here            ^ and spelled it out here, mid-fragment
    #
    # No fragment begins with the truncated name, so the scan above cannot see it. Read
    # instead from each later mention of the name to the end of that mention. The same
    # two guards apply, and they are what keeps this from over-reaching the way a plain
    # word window does -- the measured history of that is in this function's docstring.
    haystack, needle = narrative.upper(), fragment.upper()
    found = haystack.find(needle)
    while found != -1:
        candidate = _read_name(narrative[found:].split(",")[0])
        if (
            len(candidate) > len(longest)
            and fold(candidate).startswith(folded)
            and fold(candidate) != folded
        ):
            longest = candidate
        found = haystack.find(needle, found + 1)
    return longest


# The bank writes a payment as a sentence naming both sides: "PMT FRM <payer> TO <payee>".
# The comma is the bank's line wrap rather than a separator, so it is allowed inside a name.
PARTIES = re.compile(
    r"(?:PMT\s+)?(?:FRM|FROM)\s+(.+?)\s+TO\s+(?:TO\s+)?(.+?)(?=\.|,\s*$|\s+FOR\s|\s+PROJECT\s|$)"
)

# What the bank appends after a name: the reason for the payment, not part of who it was.
TRAILING_CLAUSE = re.compile(r"\s+(PROJECT|ON\s+BEHALF\s+OF|FOR)\s.*$")

# Legal forms the two sides spell differently. The master list writes `Limited`, the bank
# writes `LTD`, and without this they are simply two different strings.
LEGAL_FORMS = {"LIMITED": "LTD"}


def strip_clause(name: str) -> str:
    """Drop the reason for the payment from the end of a name.

    `NI GMF II COOPERATIEF U.A. PROJECT IAPETUS` is one counterparty and one project, and
    only the first half is who the money went to.
    """
    return tidy(TRAILING_CLAUSE.sub("", name.replace(",", " ")).strip())


def fold_legal_form(text: str) -> str:
    """`fold`, with legal forms reduced to one spelling: `... TopCo Limited` == `... TOPCO LTD`."""
    return " ".join(LEGAL_FORMS.get(word, word) for word in fold(text).split())


def locate(name: str, narrative: str) -> tuple[str, tuple[int, int]] | None:
    """Find a name in the raw narrative and return it exactly as the bank wrote it.

    A name read off a whitespace-collapsed copy of the text has lost the line wrap the
    bank put inside it -- `NORDVIK, INFRASTRUCTURE V CN SCSP` comes back as
    `NORDVIK  INFRASTRUCTURE V CN SCSP`. Both the value the reviewer reads and the span
    the screen highlights have to be the statement's own characters, so the words are
    matched back against the raw text with the wrap allowed between them.
    """
    if not name.split():
        return None
    pattern = r"[,\s]+".join(re.escape(word) for word in name.split())
    found = re.search(pattern, narrative, re.IGNORECASE)
    return (found.group(0), found.span()) if found else None


def other_party(narrative: str, own_names: list[str]) -> tuple[str, tuple[int, int]] | None:
    """The side of a `FROM ... TO ...` sentence that is not this account.

    The bank leads a narrative with a name, and usually that name is the counterparty --
    but on a transfer between two of the fund's own vehicles it leads with an alias of the
    account the statement belongs to, and the real counterparty is named in the sentence
    that follows. `NORDVIK I.A.B. FUND I, TFR+ PMT FRM NI ABF II SCSP TO NI ABF I SCSP`
    is the statement for NI ABF I, so the counterparty is NI ABF II.

    Whichever of the two sides is not this account is the answer, which is a rule about
    the transaction rather than about the words, and does not need a list to apply.
    """
    found = PARTIES.search(" ".join(narrative.upper().split()))
    if not found:
        return None
    mine = {fold_legal_form(name) for name in own_names if name}
    for side in found.groups():
        name = strip_clause(side)
        if not name or fold_legal_form(name) in mine:
            continue
        return locate(name, narrative) or (name, None)
    return None


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


def match_by_legal_form(name: str, lists: list[tuple[str, list[str]]]) -> Match | None:
    """A match that only the legal form was hiding.

    `NI V AZURITE HOLDCO LTD` and `NI V Azurite HoldCo Limited` are the same company, and
    every comparison in `match` misses them: they are not equal, neither opens the other,
    and `LTD` against `LIMITED` breaks the token overlap.

    Deliberately a fallback rather than another tier inside `match`. Reducing `Limited` to
    `Ltd` collapses entries the master lists keep apart, so it is worth doing when the
    alternative is no answer at all, and not worth doing when there is already a real one.
    """
    target = fold_legal_form(name)
    if not target:
        return None
    for rank, (list_name, entries) in enumerate(lists):
        for entry in entries:
            if fold_legal_form(entry) == target:
                return Match(entry, round(0.88 - rank * 0.02, 2), list_name)
    return None
