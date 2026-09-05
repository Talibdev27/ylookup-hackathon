# Deals and positions

The last two columns, and the only ones that read a 6,635-row master. The human filled
both on the same 30 of 100 rows.

| Column | Human | Now |
|---|---|---|
| `resolved_deal` | 30 filled | 25 / 30 agree |
| `resolved_position` | 30 filled | 13 / 30 agree, 13 more shortlisted |

A deal is the investment a payment belongs to. A position is the specific holding under
that deal — the same deal usually has an equity position and a funding-loan position, and
sometimes several of each.

Both come out of one sheet, `Deal & Position Master List`, which carries a `Deal Name` and
a `Position` on every row along with the legal entity that holds it and the security type.

---

## The gate is the whole trick

6,635 rows is far too many to search with a bank narrative. What makes it tractable is
knowing when *not* to search:

> Every one of the 30 rows the human gave a deal is one we classify `Investment` or
> `Investment Transfer`. Only one row we classify that way carries no deal.

So `resolved_deal` reads `classification` first and stops there on 70 rows. A bank fee has
no deal because there is no investment behind it; neither does an internal transfer or a
supplier payment. Saying nothing is the correct answer, and it is a different answer from
"we could not find one".

Without the gate, every one of those 70 rows would get the nearest name in a 6,635-row
list, which is exactly the confident-wrong-value failure the product argues against.

---

## Which name to look up

The two investment kinds are not interchangeable, and using the wrong one silently
produces a plausible deal that is not this deal.

| Kind | What is happening | The lookup |
|---|---|---|
| `Investment` | money moving **into** a holding company | the **counterparty** — that company *is* the deal |
| `Investment Transfer` | money moving **between the fund's own vehicles** to finance something | the **project** — the vehicles are not the deal |

```
Investment           NI V AZURITE HOLDCO LTD, ... EQUITY: ...
                     └─ counterparty ─→ deal `NI V Azurite HoldCo Limited`

Investment Transfer  NORDVIK INFRA.V CN SC, SHORT TERM LOAN: FROM NI V SCSP TO NI V CN SCSP
                     both sides are ours ─→ look up the project instead
```

**A deal is not always named after its project.** `Azurite Array` is financed through
`NI V Azurite HoldCo Limited`, which does not carry the project name anywhere in it. The
*positions* underneath it do, so when no deal name matches the project, the position text
is searched instead.

**Several deals is a real answer.** A project financed through four holding vehicles has
four deals. The human joined them with ` | ` rather than picking one, so that is what
happens here, at `needs_review`.

Currency breaks ties throughout: `NI GMF II Coöperatief U.A. - USD` and `- EUR` are one
counterparty held twice, and the row's own currency says which.

---

## Narrowing to one position

Given the deal, its positions are filtered three ways:

1. **The legal entity** whose statement this is — `matched_legal_entity`, which is 100/100.
2. **Equity or funding loan**, from how the bank describes the purchase:

   | The bank writes | Security |
   |---|---|
   | `ACQ 100PER OF SHARES IN ...`, `EQUITY:` | Equity |
   | `PURCHAS 100PER OF LOAN PRINCIP`, `LOAN:` | Funding loan |
   | `PURCHASE 100PER OF ACC INT` | Funding loan — accrued interest is part of the loan |

3. **The project named in the position text**, which separates the six holdings under
   `NI GMF II Coöperatief U.A. - USD` (Atria, Tansymoor, Iapetus, Bragi, Elmwood, OFW-XX-1).

Each filter is applied only if it leaves something behind. A filter that would empty the
list is a filter based on something the bank did not say, so it is skipped rather than
allowed to produce nothing.

---

## When the answer is not in the bank text

That leaves exactly one position on 13 rows. On the rest it does not, and the reason is
worth being precise about, because it is not a gap in the matching.

```
Cephalus Biogas 001 Limited - EUR (Halstead (Equity))
Cephalus Biogas 001 Limited - EUR (Equity)
```

Both are real positions. Same deal, same legal entity, same security type, both live in
the master. The narrative reads:

```
NI ABF I SCSP, PMT FRM NI ABF II SCSP TO NI ABF I, SCSP FOR ACQ 100PER OF SHARES IN,
CEPHALUS BIOGAS 001 LTD REL TOTAL ...
```

Nothing in it says `Halstead`. No amount of matching recovers a word that was never
written, and the human's answer is not reconstructible from what the bank sent.

So those rows carry **every candidate** under the human's own heading:

```
Review - multiple positions: <position> | <position>
```

That string is not invented. It is what their working file says on the Fenwick row, where
eighteen positions fitted and they wrote all of them out rather than choosing.

### What that costs, and what it buys

| Outcome | Rows |
|---|---|
| exact answer | 13 |
| shortlist, **and the human's answer is on it** | 13 |
| shortlist, human's answer not on it | 3 |
| one answer, wrong | 1 |

The scoreboard reads this as 13/30 with 17 wrong, which undersells it: on **26 of the 30
rows** the reviewer is either handed the answer or handed a two-to-four item list with the
answer on it. The one remaining single wrong answer is inherited from a wrong deal.

Picking the first candidate instead of listing them would score roughly six more and turn
thirteen honest shortlists into thirteen coin tosses presented as answers.

---

## What it still gets wrong

Five deals miss. Four are confident, and none of the four is a matching failure:

| Rows | Why |
|---:|---|
| 3 | the human booked `ZZZ Operations EUR` / `GBP` — **strings that appear nowhere in the deal master** |
| 1 | the human put a *position* string in the deal column: `Cephalus Biogas 001 Limited - EUR (Halstead (Funding Loan))` |
| 1 | Fenwick: five deals carry the project, the human listed four, with no rule visible for the one they dropped |

`ZZZ Operations` occurs in exactly two places in the workbook — the `Staging Sheet` and the
`DIU ` output. It is an admin bucket that exists in their process and not in the reference
data they gave us, so nothing here can derive it. That is worth showing the client rather
than working around: a value that reaches the journal but is not in any master list is the
kind of thing nobody checks.

---

## Working on this

```bash
./run.sh
```

Both columns print per run. The gate is the load-bearing part — if `classification` moves,
these move with it, so check all four numbers together.

The stages run in registry order and `resolved_position` reads what `resolved_deal` wrote,
so the two are tested as a pair. `tests/test_stages.py` builds a two-position
`ReferenceLists` in memory; no workbook needed.

See also [counterparty-matching.md](counterparty-matching.md) — `resolved_deal` is only as
good as the counterparty and project feeding it.
