# Counterparty matching

Two columns, and the reason the product exists. The human doing this by hand pulled a
name out of the bank text on 55 of 100 rows and identified it on 48. The 52 they left
blank are the opportunity; the rows they filled are the check on whether we agree.

| Column | Human | Now |
|---|---|---|
| `pulled_out_sender_beneficiary` | 55 filled | 45 / 55 agree |
| `matched_sender_beneficiary` | 48 filled | 31 / 48 agree, 8 / 52 net new |

Two stages, kept apart on purpose: extraction and matching fail differently, and a
reviewer looking at a wrong answer needs to see which half went wrong.

---

## Why it is hard

The two sides are spelled differently on purpose, and every one of these is a real row.

| The bank writes | The master list holds |
|---|---|
| `NI ABF II MIZARCO S.A R.` | `NI ABF II MizarCo S.à r.l.` |
| `NI V AZURITE HOLDCO LTD` | `NI V Azurite HoldCo Limited` |
| `TRENTBECK AUDIT LUXEMBOURG` | `Trentbeck Audit - Lu` |
| `NORDVIK I.A.B. FUND I` | `Nordvik Infrastructure Advanced Bioenergy Fund I SCSp` |

The bank writes uppercase ASCII with no accents, truncates where it runs out of line, and
wraps mid-word with a comma at the wrap point. The master lists write the legal name with
accents, legal suffixes and office codes. Nothing matches as text, so every comparison
happens on a **folded** form — accents stripped, punctuation dropped, uppercased.

```
NI ABF II MizarCo S.à r.l.   ─┐
                              ├─ fold ─→  NI ABF II MIZARCO S A R L
NI ABF II MIZARCO S.A R.L.   ─┘
```

---

## Stage 1 — extraction

`pulled_out_sender_beneficiary`. The name as the bank wrote it, with the character span it
sits at, because that span is what the review screen highlights.

The narrative is comma-separated fragments. The counterparty is normally the first one
that looks like a name rather than a reference:

```
NI ABF I SCSP, PMT FRM NI ABF II SCSP TO NI ABF I, SCSP FOR PURCHASE 100PER OF ACC INT
└─ the name ─┘
```

Three things then happen to it.

**Completion.** The bank truncates at the line break, and often the full form appears
later in the same text. Only whole comma-fragments are considered as completions. That
limit is deliberate and was measured — see the table in `complete()`; the loosest version
scored 7/55 against the simplest at 37/55.

**Clause stripping.** `NI GMF II COOPERATIEF U.A. PROJECT IAPETUS` is one counterparty and
one project. Everything from `PROJECT`, `FOR` or `ON BEHALF OF` onwards is why the payment
happened, not who it was with.

**The other-party rule.** This is the one worth understanding.

The bank leads with a name, and usually that name is the counterparty. But on a transfer
between two of the fund's own vehicles, it leads with an alias of *the account the
statement belongs to*, and names the real counterparty in the sentence that follows:

```
statement for: NI ABF I SCSp

NORDVIK I.A.B. FUND I, TFR+ PMT FRM NI ABF II SCSP TO NI ABF I, SCSP FOR ACQ ...
└─ an alias of us ─┘             └─ the counterparty ─┘
```

So when the text says `FROM x TO y`, the side that is **not this account** is the answer.
That is a rule about the transaction rather than about the words.

It fires on one condition only: **the name we read is on none of the reference lists.** A
narrative that names its counterparty up front is never second-guessed. Applied to every
row instead, it drops the match rate from 25/48 to 16/48 — it was measured both ways.

It lives in the extraction stage, not the matching stage, so both columns say the same
thing about the same row.

---

## Stage 2 — matching

`matched_sender_beneficiary`. The pulled name against the reference lists, in the order
the `Process` sheet reviews them:

```
Related Party → Legal Entity → Investor → Vendor → Deal & Position
```

Order is the rule. A counterparty that is a related party is a related party, even when
the same name also appears as a vendor. Deals are last but present, because some
counterparties are held per currency and exist only there.

`counterparty.match` scores four kinds of agreement, best first:

| | Confidence |
|---|---|
| folded forms are equal | 0.98 |
| equal once the master's office suffix is dropped (`- Lu`, `- Non-LU`) | 0.92 |
| one opens the other | 0.62 – 0.90, by how much overlaps |
| token sets are nested and overlap ≥ 60% | 0.55 – 0.85 |

Each list further down costs 0.02, so priority breaks ties without hiding a better match.

**Currency decides between twins.** `NI GMF II Coöperatief U.A.` and
`... U.A. - USD` are one counterparty held in two currencies. The narrative never says
which; the row's own currency does. A matching currency adds 0.16, a mismatched one takes
0.20 — enough for a currency-tagged deal entry to outrank a currency-blind exact match on
an earlier list.

**Legal form, as a fallback.** `NI V AZURITE HOLDCO LTD` and `NI V Azurite HoldCo Limited`
defeat all four comparisons above: not equal, neither opens the other, and the token
overlap breaks on the last word. So `Limited` reduces to `Ltd` and the comparison runs
again — but only when the alternative is no answer at all, because that reduction
collapses entries the master lists deliberately keep apart.

**One entity, several spellings.** 38 entities sit on more than one sheet spelled
differently:

```
Related Party Master          NI DRACONIS HOLDCO I SCSp     NI V Kalvik TopCo Limited.
Deal & Position Master List   NI Draconis HoldCo I SCSp     NI V Kalvik Topco Limited
```

They are the same company, so which spelling gets written out is a choice. The deal master
wins, because that is the register the journal entries load against.

Only the **spelling** moves. Which list the name was *found* on is a different fact, and
`classification` reads it to decide whether a row is a `Vendor` or an `Investment`, so the
source stays put. `ReferenceLists.canonical_spelling` does the one and leaves the other.

---

## What was tried and rejected

**Expanding the bank's abbreviation against the legal entity list.** `NI ABF II SCSP`
expands cleanly to `Nordvik Infrastructure Advanced Bioenergy Fund II SCSp`, and the
machinery already exists in `abbreviations.py` for exactly this. It scores **worse**:
28/48 with it, 29/48 without.

The reason is that the human records the *short* master spelling — `NI ABF I SCSp`, which
is on the related party master — so expanding it to the full fund name is the wrong
direction. Where the short form is not on any list, the long one is right; where it is,
expanding overshoots. That is a per-row question, and the priority order already answers
it, so the expansion earns nothing.

**Applying the other-party rule everywhere.** 25/48 → 16/48. Recorded above.

---

## What it still gets wrong

14 of the 48 disagree with the human. **Eleven of them go to a reviewer** rather than
booking through.

| Rows | We say | Human says | Why |
|---:|---|---|---|
| 6 | `NI ABF II Co-Invest SCSp` | `Nordvik Infrastructure Advanced Bioenergy Fund II SCSp` | `NI ABF II SCSP` is not on any list; the co-invest vehicle is the nearest thing that is |
| 5 | `Nordvik Infrastructure Partners Inc.` | `NIP P/S` | two entities of the same group; nothing in the text separates them |
| 3 | same company, other spelling | | the lists disagree and neither is wrong |

The first two families need knowledge that is not in the bank text or the lists — which is
what the review queue is for. The third is a data-quality fact about the client's own
workbook and is worth showing them.

---

## Working on this

The scoreboard is the arbiter:

```bash
./run.sh
```

Both columns are printed per run. A change that lowers either one gets reverted, however
convincing the reasoning was — everything in the *rejected* section above was convincing.

Measure each change on its own before combining them. Two of the three that landed here
looked identical in the aggregate and only separated when run one at a time.

Stage tests need no workbook: `tests/test_stages.py` builds a three-line `ReferenceLists`
in memory.
