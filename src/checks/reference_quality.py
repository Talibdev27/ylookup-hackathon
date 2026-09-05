"""Near-duplicate entries in a reference master list -- a data-entry inconsistency
rather than a matching problem.

The whole matcher resolves counterparties against the `Legal Entity Master List` sheet
(97 rows, one column `Legal Entity`, read via `src.spine.build.load_workbook()`). If that
list itself holds two rows for what is really one legal entity -- the same name typed
two different ways -- every match against the shorter or longer spelling silently splits
what should be one counterparty's activity into two. That is a defect in the reference
data, not in a bank narrative, so it gets its own check rather than living inside the
matcher.

Two ways a pair of entries counts as a near-duplicate here:

  1. Exact fold collision -- two different raw strings that `src.matcher.counterparty.fold()`
     reduces to the same value. `fold()` already strips accents, punctuation and case, which
     is exactly what makes `NI ABF II MizarCo S.a r.l.` and `NI ABF II MIZARCO S A R L`
     the same folded string; two master-list rows landing on the same folded value can only
     be the same entity typed two different ways. Unambiguous, so this is `error` severity.

  2. Token superset with high overlap -- one entry's folded, whitespace-split token set is
     a strict subset of the other's, and the overlap coefficient (|smaller| / |larger|) is
     >= 0.9. This is `review`, not `error`, on purpose -- see the threshold note below.

Threshold: 0.9, checked against the real 97-row bundled list before picking it. At 0.9 the
list produces exactly 11 candidate pairs, and *every one* of the 11 differs from its
partner by exactly one token that is a meaningful fund-structuring qualifier -- "NON" (a
"Non-US" vs "US" blocker: two different parallel vehicles), "ELIMINATION"/"ELIMINATIONS"
(a consolidation-elimination entry is its own distinct legal entity, not a typo'd version
of the fund it eliminates), or "BLOCKED". None of the 11 are data-entry duplicates -- a
fund administration entity list is *expected* to hold many genuinely-different vehicles
that share almost all of their name (same fund family, different currency/feeder/blocker/
elimination leg). Loosening the threshold below 0.9 only pulls in more of exactly that
noise (44 pairs at 0.8); tightening it above ~0.92 finds nothing at all on this list.
0.9 is kept anyway, flagged as `review` rather than `error`, because a human confirming
"these 11 are not duplicates" is one glance per pair -- cheap enough that surfacing the
candidates is still worth doing on a list this size, and the alternative (silence) is
indistinguishable from "nobody looked."

So: on the bundled 97-row list, check 1 (exact fold collision) finds zero -- a genuinely
clean answer, not an assumption -- and check 2 finds 11 candidates that manual review
confirms are all legitimate distinct entities, not errors.
"""
from __future__ import annotations

from src.checks.contract import Flag
from src.matcher.counterparty import fold

OVERLAP_THRESHOLD = 0.9


def check(legal_entities: list[str]) -> list[Flag]:
    """One flag per near-duplicate pair found in `legal_entities`."""
    flags: list[Flag] = []
    names = [n for n in legal_entities if n and n.strip()]

    by_fold: dict[str, list[str]] = {}
    for name in names:
        by_fold.setdefault(fold(name), []).append(name)

    exact_dupe_names: set[str] = set()
    for folded, variants in by_fold.items():
        unique_variants = sorted(set(variants))
        if len(unique_variants) < 2:
            continue
        exact_dupe_names.update(unique_variants)
        for i in range(len(unique_variants)):
            for j in range(i + 1, len(unique_variants)):
                a, b = unique_variants[i], unique_variants[j]
                flags.append(
                    Flag(
                        check="legal_entity_exact_fold_duplicate",
                        severity="error",
                        message=(
                            f"{a!r} and {b!r} are typed differently but fold to the same "
                            f"value ({folded!r}) -- almost certainly the same legal entity "
                            f"entered twice"
                        ),
                        source={"a": a, "b": b},
                        expected="one entry per legal entity",
                        actual=[a, b],
                    )
                )

    # Token-superset overlap, skipping any name already flagged as an exact fold
    # collision -- that pair already has its answer, a token-overlap flag on top would
    # just be noise about the same two rows.
    tokens = {name: set(fold(name).split()) for name in names}
    unique_names = sorted(set(names) - exact_dupe_names)
    for i in range(len(unique_names)):
        for j in range(i + 1, len(unique_names)):
            a, b = unique_names[i], unique_names[j]
            token_a, token_b = tokens[a], tokens[b]
            if not token_a or not token_b:
                continue
            if not (token_a <= token_b or token_b <= token_a):
                continue
            smaller, larger = sorted((token_a, token_b), key=len)
            overlap = len(smaller) / len(larger)
            if overlap < OVERLAP_THRESHOLD:
                continue
            shorter_name, longer_name = (a, b) if token_a is smaller else (b, a)
            flags.append(
                Flag(
                    check="legal_entity_near_duplicate",
                    severity="review",
                    message=(
                        f"{shorter_name!r} is a token subset of {longer_name!r} "
                        f"({overlap:.0%} overlap) -- confirm these are two different "
                        f"legal entities, not one entity entered inconsistently"
                    ),
                    source={"shorter": shorter_name, "longer": longer_name},
                    expected=None,
                    actual=round(overlap, 4),
                )
            )

    return flags
