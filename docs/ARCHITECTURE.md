# Architecture

The backend end to end: what each piece owns, what it reads and writes, and how one
transaction moves from a PDF to a reviewed answer. `CONTEXT.md` defines the vocabulary
used here; `CONTRACT.md` owns the exact row shape; this document is the map connecting
them. Frontend design is out of scope here on purpose — that is being worked separately.

Numbers in this document are a snapshot, not a promise. Run `./run.sh` for what is true
right now; the scoreboard is the arbiter, not this file.

---

## 1 · The shape of it, in four stages

The pitch describes four agents. Here is where each one actually lives:

| # | Agent | What it does | Code |
|---|---|---|---|
| A | **Pull data** | Read a PDF, get text and tables out of it | `src/extraction/pdf_text.py` (any PDF), `src/spine/pdf.py` (bank statements specifically) |
| B | **Convert** | Raw text into structured records with a fixed shape | `src/contract.py` (`Row`/`Raw`), `src/matcher/normalise.py` |
| C | **Match & import to Excel** | Resolve each record against the reference data, produce output | `src/matcher/` (stages, matching, scoring), `src/exporter.py`, `src/extraction/workbook_writer.py` |
| D | **Reviewer — find inconsistency** | Surface what the machine is unsure of, or what does not add up | `src/ui/` (human review queue), `src/checks/` (automated inconsistency flags) |

Stage D is two things wearing one label on the whiteboard: a human reviewing what the
matcher flagged as uncertain, and an automated check catching something that is
internally inconsistent regardless of whether any single field looks wrong. Both produce
the same kind of thing — a finding with a reason and a source — which is why `Flag` in
`src/checks/contract.py` is deliberately shaped like `Field` in `src/contract.py`.

Only stage C has a document type built out today (bank statements → journal-entry
fields). Stages A and B are already document-agnostic underneath; a second document type
needs its own C, on the same A and B. See `docs/ROADMAP.md`.

---

## 2 · The contracts that pass between stages

Everything above talks to everything below it through one of two small, fixed shapes.
Neither stage is allowed to invent its own — that discipline is what lets a stage be
tested with a three-line fake instead of a real workbook.

**`Row`** (`src/contract.py`) — one transaction. Carries `source` (which PDF, which
page), `raw` (the statement's own values — account, currency, narrative, credit, debit,
balance), and `fields` (what the matcher has worked out so far).

**`Field`** — one answer about a row. Never a bare value:

```
value        the answer, or None
confidence   0.0 - 1.0
status       "auto" | "needs_review" | "unresolved"
evidence     an Evidence — where this came from
alternatives what else was considered and rejected
```

**`Evidence`** — a character span into `raw.narrative_raw`, which reference list (if any)
the value was found in, and a plain-English reason. `evidence.text` is written to be read
by a fund manager verbatim; nothing technical belongs in it.

**`ReferenceLists`** (`src/matcher/reference.py`) — the only thing a matching stage is
told about the world beyond its own row: legal entities, related parties, investors,
vendors, deal names, project codes. Built once per run, from the client's workbook or
from a bare in-memory fake in tests. Owns every sheet name and column name in the
workbook, so a renamed sheet breaks in exactly one place.

**`Flag`** (`src/checks/contract.py`) — one finding from a check: `check` (which one),
`severity`, `message` (fund-manager language, like `Evidence.text`), `source`, and what
was `expected` versus what was `actual`. A check's signature is always
`(records) -> list[Flag]`.

---

## 3 · Stage A — pull data

**`src/extraction/pdf_text.py`** is the primitive: any PDF in, page text and page tables
out (`ExtractedDocument`). It knows nothing about bank statements, balance sheets, or
anything else — it is pure PDF mechanics, built on `pdfplumber`.

**`src/spine/pdf.py`** is the one parser built on that primitive so far. It knows the
specific shape of a bank statement: one transaction table per page, a `Narrative` row
glued to the row above it, a bank reference that sometimes wraps onto its own
continuation line. Output is a list of `Row` objects, `raw` fully populated, `fields`
empty.

Two things this stage gets right that are easy to get wrong, both covered by regression
tests in `tests/test_spine.py`:

- **Row order is print order, not chronological order.** Statements print newest
  transaction first. This matters again in stage D.
- **A wrapped bank reference is not a new transaction.** It is detected by a strict
  pattern (`CONTINUATION`) and appended to the row above, so it is not mistaken for a
  `Balance brought forward` separator, which has the same one-cell shape.

**`src/spine/xlsx.py`** belongs here too, on the reference-data side: a dependency-free
`.xlsx` reader, written specifically because the reference workbook has three traps that
break a naive reader silently — blank cells omitted from the sheet XML (so cells must be
placed by their `r=` reference, never positionally), HTML-escaped text (`Co&#246;peratief`),
and dates stored as Excel serials. `src/spine/build.py` calls it and, for the bundled
sample only, asserts every sheet's row count against a known value — real uploads are not
held to somebody else's row counts.

---

## 4 · Stage B — convert

This stage turns what stage A extracted into the structured form everything downstream
actually reasons about.

For bank statements, most of this is already done by the time `Row` objects exist —
`raw` is populated directly by the parser. The real work here is **normalisation**:
`src/matcher/normalise.py` turns

```
NI ABF I SCSP, PMT FRM NI ABF II SCSP TO NI ABF I, SCSP FOR PURCHASE 100PER OF ACC INT
```

into a normalised, comparable form, while returning an index map back to the original
characters — because every `Evidence.span` highlighted on screen has to point at the raw
text the reviewer is looking at, not a cleaned-up copy of it. `src/matcher/counterparty.py`
does the equivalent folding for names (`fold()`): strips accents, punctuation and case, so
`NI ABF II MizarCo S.à r.l.` and `NI ABF II MIZARCO S.A R.L.` compare equal.

For a future document type, this is where its own structuring logic goes — turning
whatever `pdf_text.extract()` returned into a list of dict records with a stable set of
keys, the way `spine/pdf.py` turns pages into `Row`s. `src/extraction/workbook_writer.py`
is the mirror image: structured records back out to a formatted `.xlsx`, one sheet per
document type.

---

## 5 · Stage C — match and import to Excel

This is where most of the built system lives: `src/matcher/`.

**`stages.py`** holds ten functions, one per output column, each with the exact
signature `(row: Row, lists: ReferenceLists) -> Field`. All ten are now written. They run
in a fixed order — `REGISTRY`, at the bottom of the file — because later stages read
fields earlier stages wrote (`classification` reads `matched_sender_beneficiary`;
`counterparty_transtype` reads `classification`). A stage not yet written raises
`NotImplementedError`, which the runner treats as a declaration, not a failure — see
`src/matcher/run.py`'s three-way split between *applied*, *not written yet*, and
*failed*; that path stays live for whichever stage is next to be improved.

Two stages are pure lookups against derivable facts (`matched_legal_entity`,
`cash_leg_transtype`). Four chain off each other:

```
pulled_out_sender_beneficiary   -- extract the name as the bank wrote it (counterparty.extract)
        |
matched_sender_beneficiary      -- resolve it against the reference lists (counterparty.match)
        |
classification                  -- which reference list it resolved against, or what the
        |                          narrative says the payment was for (NARRATIVE_RULES)
        |
counterparty_transtype          -- which account the other side books to, derived from
                                    classification + direction of money (COUNTERPART_ACCOUNTS)
```

`matched_project_code` runs a similar three-source cascade independently: the bank's own
wording for overhead rows (`OH - Bank Fees`, `OH - Interest Income`), a named
`PROJECT <name>` looked up against the project report, then a project name mentioned in
passing (guarded against matching a counterparty name by accident).

The last two, `resolved_deal` and `resolved_position`, read `classification` the same
way `counterparty_transtype` does: only the rows classified `Investment` or `Investment
Transfer` carry a deal at all, which turns a 6,635-row master into a search worth doing
on 30 rows instead of 100. `docs/deal-resolution.md` covers the gate and what it costs to
get right.

**`counterparty.py`** and **`abbreviations.py`** are the matching primitives `stages.py`
calls: `abbreviations.expand()` bridges the bank's initialism (`NI ABF II SCSP`) to the
master list's full name; `counterparty.match()` searches the reference lists in the
Process sheet's own priority order (related party, then legal entity, then investor,
then vendor, then deal) and breaks currency-suffix ties using the row's own currency.
`docs/counterparty-matching.md` covers why this pair is the hardest column on the sheet
and what three rejected approaches cost against the ground truth.

**`score.py`** is not part of the pipeline — it grades pipeline output against
`Staging Sheet`, the human's own 100 answers, joining rows to ground-truth records on a
composite key (narrative + amount + bank reference + account number) rather than by
position, because the two are not in the same order. Two numbers per column:
**agreement** (of what the human filled in, how much do we reproduce) and **net new** (of
what they left blank, how much do we resolve).

**Getting it to Excel/CSV:**

- `src/exporter.py` turns the reviewed queue into a CSV: one row per transaction, the
  matcher's answer or the reviewer's correction (reviewer wins, including a reviewer's
  decision to give up, which clears the value rather than falling back to a guess that
  was already rejected), and who decided each one.
- `src/extraction/workbook_writer.py` is the more general form for a future document
  type: any `{"sheet name": [records]}` to a formatted, multi-sheet `.xlsx`. Not wired
  into the bank-statement pipeline, which has its own CSV exporter already; this is for
  whatever stage C looks like for a second document type.

---

## 6 · Stage D — reviewer: find inconsistency

Two different mechanisms, one purpose.

**The human review queue** (`src/ui/app.py`) reads `data/rows.json`, finds every row with
at least one field whose `status` is not `"auto"`, and presents it as a question: what
does the bank text say, what did the matcher propose, why. A reviewer's decision
(`approve` / `alternative` / `manual` / `unresolved`) is stored in `data/decisions.json`,
keyed by row id and then by field, and always wins over the matcher's proposal.
`src/ui/labels.py` is the one place any of this gets put into words a fund manager would
read — field keys, confidence floats and currency codes never reach a template directly.

**The automated checking agent** (`src/checks/`) runs over already-structured records
looking for something that does not add up, independent of whether any single field's
confidence looks low. It is a different question from what the matcher asks: the matcher
asks *"what is this?"*, a check asks *"does this reconcile?"*. `footing.py` is the first
one — balance continuity. It matters that statements print newest-first (stage A's note
above): the check reverses each account's rows into chronological order before checking
that `balance[i] == balance[i-1] + amount[i]`, which was verified by hand against every
one of the 100 real transactions before being written as a check. It currently finds
nothing on the bundled data, which is the correct answer — those statements foot.

Neither mechanism is wired to the other yet. A `Flag` from `src/checks/` is not currently
rendered in the review queue; `docs/ROADMAP.md` and the frontend work cover that.

---

## 7 · The two ways in, and where state lives

**Command line**: `python -m src.pipeline` runs stage A through C once, writes
`data/rows.json`, and deletes `data/decisions.json` — a fresh run invalidates old
decisions because they are keyed by row id, which is positional, and a stale decision
could silently reattach to a different transaction. `python -m src.matcher.score` then
grades `rows.json` against `Staging Sheet`. `run.sh` is both, back to back.

**The web app**: `serve.py` starts `src/ui/app.py`. `/upload` accepts a reference
workbook and/or a set of statement PDFs, validates them (right extension, workbook
present if none is set up yet), stores them under `data/workspace/`, and calls the exact
same `pipeline.run()` the CLI does — there used to be three separate copies of this
orchestration with drifted behaviour, which is why `src/pipeline.py` exists as the single
entry point both paths now share. `/` is the review queue. `/rows/<id>/decide` records a
reviewer's answer. `/export.csv` streams the reviewed queue out.

**State is files, not a database**, on purpose: `data/rows.json`, `data/decisions.json`,
and whatever is in `data/workspace/`. This is a deliberate hosting decision
(`docs/TASK-hosting.md`) — one instance, one worker, a persistent disk if the platform
offers one. Two workers would each have their own filesystem view and could serve a
half-loaded queue; a second instance would disagree with the first about what was just
uploaded.

---

## 8 · Following one transaction all the way through

The EUR 0.44 bank charge on `NI ABF I SCSP`'s statement, concretely, stage by stage:

1. **Pull data.** `spine/pdf.py` reads page 1 of the statement PDF, finds the row with
   bank reference `NONREF`, debit `-0.44`, and the glued-on narrative
   `CHARGES FOR 2, OUTWARD SEPA PAYMENT`. Produces a `Row` with `raw` populated,
   `source = {"pdf": "...0894.pdf", "page": 1}`.

2. **Convert.** `normalise()` turns the narrative into a comparable uppercase form and
   records the index map back to the original text.

3. **Match & import.** `matched_legal_entity` expands `NI ABF I SCSP` against the legal
   entity master list. `pulled_out_sender_beneficiary` finds nothing nameable in the
   narrative (`CHARGES FOR 2` is a fee description, not a name), so
   `matched_sender_beneficiary` also comes back empty. `matched_project_code` matches
   `CHARGES FOR` against `OVERHEAD_PHRASES` and returns `OH - Bank Fees` with high
   confidence. `classification` matches the same phrase and returns `Other`.
   `cash_leg_transtype` sees a debit and returns `Cash - Disbursed - EUR` at full
   confidence. `counterparty_transtype` reads `classification = Other` and the outgoing
   direction, and returns `Expense - Bank Charges` from `COUNTERPART_ACCOUNTS`.

4. **Reviewer.** Every field above resolved at `status = "auto"`, so this row never
   appears in the human review queue — it is one of the rows the matcher is confident
   about. `checks/footing.py` includes it in its balance-continuity pass for this
   account; it foots, so it produces no flag either.

5. **Out.** `exporter.to_csv()` includes the row with `matcher` as the source for every
   field, since no reviewer decision exists for it.

A row that *does* need a human — say, one where `matched_sender_beneficiary` finds no
match on any list — stops being silent at step 3: it comes back `status = "unresolved"`
with `evidence.text` naming what was searched, appears in the queue at step 4, and
whatever the reviewer decides is what step 5 exports.

---

## 9 · Extension points

Adding a matcher stage: one function of shape `(row, lists) -> Field` in
`src/matcher/stages.py`, one line in `REGISTRY`. `AGENTS.md` covers this.

Adding a check: one function of shape `(records) -> list[Flag]` in `src/checks/`, tested
against real data both clean and deliberately broken — `tests/test_footing.py` is the
template. See `docs/ROADMAP.md`.

Adding a second document type: a new parser over `src/extraction/pdf_text.py`, mirroring
what `spine/pdf.py` does for statements, producing records that `workbook_writer.py` can
render and that `src/checks/` can run over unchanged, since checks do not know or care
which document type a record came from. See `docs/ROADMAP.md` for why bank statements are
the only document type with real sample data today, and what the fallback is.
