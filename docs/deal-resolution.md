# Deals and positions

The last two columns, and the only ones that read a 6,635-row master. The human filled
both on the same 30 of 100 rows.

| Column | Human | Now |
|---|---|---|
| `resolved_deal` | 30 filled | 26 / 30 agree |
| `resolved_position` | 30 filled | 26 / 30 agree |

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

## When two positions both fit

The three filters leave exactly one position on many rows and two or four on the rest.
Where several remain, two things decide, and neither is in the bank text -- both come out
of the master's own shape, so both are proposed at `needs_review` with the rejected
candidates kept beside them.

**The most specific holding wins.** The master usually carries the same holding twice: a
roll-up at the deal, and the underlying asset named inside it.

```
Cephalus Biogas 001 Limited - EUR (Equity)                 <- the roll-up
Cephalus Biogas 001 Limited - EUR (Halstead (Equity))      <- the asset inside it
```

The payment belongs to the named one. The roll-up is where it lands afterwards.

**Except on the paying side of a transfer between two of the fund's own vehicles.** Both
legs of four such transfers are in the sample, and they book at different levels: the fund
receiving the money takes on the underlying holding, and the fund paying is funding the
other's deal rather than acquiring anything itself, so it books at the deal. Same
narrative, opposite sign, different answer -- which is why direction alone does not
explain it and `classification` has to be read too.

**And a deal only counts if it holds the security that was bought.** A project financed
through several vehicles is not financed the same way through all of them. One of the five
Fenwick deals holds only equity; the payment is a short-term loan, so it is not one of this
payment's deals. That is the rule behind the human listing four of the five.

The bank names the security three ways -- as a heading (`EQUITY:`), as what was bought
(`ACQ 100PER OF SHARES`), and in brackets after the company (`... 001 LTD (EQUITY)`). The
third is easy to miss because the word abuts its punctuation.

## What it still gets wrong

Four rows on each column, and none of them is a matching failure.

| Rows | Why |
|---:|---|
| 33, 34 | The fund settled a payment **on another vehicle's behalf**. It acquired nothing, so the deal belongs to whoever received the money -- the receiving legs of these same transfers are in the sample and do carry it. The working file books this side to an operations bucket named in no reference list, so the row is declined rather than answered with an invented value. |
| 86 | Booked to `ZZZ Operations GBP`, and structurally identical to rows 94 and 97 -- same account, same `SHORT TERM LOAN: FROM NI V SCSP TO NI V CN SCSP`, differing only in the project named. Those two get real deals. |
| 1 | The human put a *position* string in the deal column. |
| 97 | Our Fenwick shortlist and theirs differ by one deal of five. |

`ZZZ Operations` occurs in exactly two places in the workbook -- the `Staging Sheet` and
the `DIU ` output, both of which are the answers. It is an admin bucket that exists in
their process and not in the reference data they gave us, so nothing here can derive it.
That is worth showing the client rather than working around: a value that reaches the
journal but is in no master list is the kind of thing nobody checks.

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
