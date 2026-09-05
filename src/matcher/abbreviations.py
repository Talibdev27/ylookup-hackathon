"""Expand the bank's abbreviated names against a master list.

The bank writes `NI ABF II SCSP`. The master list holds
`Nordvik Infrastructure Advanced Bioenergy Fund II SCSp`. Bridging those two is the
shape of most of the matching work in this dataset.

The rule is an initialism, consumed greedily left to right: each abbreviated token either
matches the next master word outright, or spells out the initials of the next N words.

    NI   -> Nordvik Infrastructure
    ABF  -> Advanced Bioenergy Fund
    II   -> II
    SCSp -> SCSp

Implemented against all 97 master entries rather than the 4 that happen to appear in this
week of statements, so a new fund does not need a code change.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Expansion:
    """One master-list entry that the abbreviation could expand to."""

    value: str
    exact_tokens: int  # tokens matched as whole words rather than as initials
    total_tokens: int

    @property
    def confidence(self) -> float:
        """More whole-word matches means less guessing. A candidate matched entirely by
        initials is the weakest kind of match, so it never reaches certainty."""
        if not self.total_tokens:
            return 0.0
        return round(0.55 + 0.45 * (self.exact_tokens / self.total_tokens), 2)


def _words(name: str) -> list[str]:
    return [w for w in name.replace("-", " ").split() if w]


def _consume(tokens: list[str], words: list[str]) -> int | None:
    """Walk the abbreviation against the master words. Returns the number of tokens
    matched as whole words, or None if the entry cannot be consumed exactly."""
    index = 0
    exact = 0
    for token in tokens:
        if index < len(words) and words[index].upper() == token:
            index += 1
            exact += 1
            continue
        span = len(token)
        if index + span <= len(words) and all(
            words[index + offset].upper().startswith(token[offset]) for offset in range(span)
        ):
            index += span
            continue
        return None
    return exact if index == len(words) else None


def expand(abbreviation: str, master: list[str]) -> list[Expansion]:
    """Every master entry the abbreviation could be, best first.

    Ties are broken by whole-word matches: `NI ABF I SCSP` expands against both
    `... Fund I SCSp` and `... Fund II SCSp` (an `I` initial also opens `II`), but only
    the first matches `I` as a whole word, so it wins.
    """
    tokens = [t.upper() for t in _words(abbreviation)]
    if not tokens:
        return []
    found = []
    for entry in master:
        exact = _consume(tokens, _words(entry))
        if exact is not None:
            found.append(Expansion(value=entry, exact_tokens=exact, total_tokens=len(tokens)))
    return sorted(found, key=lambda e: (-e.exact_tokens, len(e.value)))


def is_initialism_of(abbreviation: str, name: str) -> bool:
    """True when `abbreviation` is `name` written in initials, with nothing left over.

    Stricter than `expand` on purpose. `expand` lets a one-letter token open a longer
    word, which is what makes `NI ABF I SCSP` also a candidate for `... Fund II SCSp`;
    it resolves that by ranking whole-word matches first across the candidates it is
    given. A caller asking about one name at a time has no such ranking to fall back on,
    so the same looseness turns `I` into `II` silently.

    Here every token must either be one of the name's words outright, or stand for two or
    more of them -- which is what an initialism is. `NI` for `Nordvik Infrastructure`
    passes; `I` for `II` does not.
    """
    tokens = [t.upper() for t in _words(abbreviation)]
    words = _words(name)
    if not tokens or not words:
        return False
    index = 0
    for token in tokens:
        if index < len(words) and words[index].upper() == token:
            index += 1
            continue
        span = len(token)
        if (
            span >= 2
            and index + span <= len(words)
            and all(
                words[index + offset].upper().startswith(token[offset])
                for offset in range(span)
            )
        ):
            index += span
            continue
        return False
    return index == len(words)
