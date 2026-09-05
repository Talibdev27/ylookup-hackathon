# Domain model

The terms this codebase is built out of. Add to this file when a module is named after a
concept that is not here yet.

## The work

**Statement** — one bank statement PDF, one account, one currency, covering a few
business days. The filename encodes entity, bank, currency and account short code.

**Narrative** — the free text the bank writes against a transaction. Uppercase, wrapped
mid-word at line breaks with commas at the wrap points, and truncated where the bank ran
out of line. Held as `narrative_raw`; evidence spans index into it, because that is the
text a reviewer sees on screen.

**Counterparty** — who a payment went to or came from. Written by the bank in truncated
uppercase ASCII, held in the reference lists in full with accents and legal suffixes.
Bridging those two spellings is most of the matching work.

**As-written / resolved** — every lookup answer splits in two: the words the bank
actually wrote, and the master-list entry they resolve to. `Pulled Out Sender/Beneficiary`
against `Matched Sender/Beneficiary`, `Pulled Out Project Code` against `Matched Project
Code`. Kept apart because extraction and matching fail differently, and a reviewer looking
at a wrong answer needs to see whether the bank was misread or the list was.

**Row** — one transaction on its way to becoming a journal entry. Carries the raw
statement values and a **Field** per column the matcher fills.

**Field** — one answer about a row: a value, a confidence, a status (`auto`,
`needs_review`, `unresolved`), the **Evidence** it came from, and the alternatives that
were rejected. Never a bare string: a value with no provenance cannot be reviewed.

**Evidence** — where a value came from. A span into the narrative, the reference list it
was found in, and a plain-English reason. Rendered verbatim to a fund manager, so it is
written in their language and never carries technical detail.

**Classification** — what kind of transaction a row is. Seven values, and they are the
data's rather than the documentation's: `Other`, `Internal`, `Investment Transfer`,
`Investment`, `Related Party`, `Vendor`, `Review`.

**Flag for review** — `Flag for review - no project match` is an *answer*, not a blank. It
is the client's own wording for "no code fits, a human has to pick", and reproducing it
says so out loud where an empty cell would imply nobody looked.

**Overhead row** — a transaction with no project because the counterparty is the bank
itself: charges, commissions, credit interest. Booked to an `OH -` code rather than a
project code.

**Inherited doubt** — a value is only as certain as the value it was derived from. The
Process sheet states it as *"each value is only as good as the stage before it"*, and it
is why a transaction type resting on an unsure classification comes back unsure too,
rather than presenting as settled.

## The reference data

**Reference lists** (`ReferenceLists`) — what the matcher matches against: legal
entities, related parties, investors, vendors, deals and project codes. Read from the
client's workbook. Owns the counterparty priority order and every sheet name.

**Workspace** — the data one run reads: one reference workbook and a set of statements.
The two halves resolve independently, because uploading this week's statements against
reference lists that are already set up is the normal case.

## The matcher

**Stage** — one step of the Process sheet, `(row, lists) -> Field`. Stages run in the
order declared by `stages.REGISTRY`, which is the Process-sheet order. A stage that is
not written yet raises `NotImplementedError`; anything else it raises is a defect.

**Process sheet** — the client's own stage-by-stage review guide, inside the workbook. It
is the specification for both the matcher's stages and the review queue's layout. Where
it disagrees with the data, the data wins and the disagreement is surfaced to a reviewer.

**Ground truth** — the `Staging Sheet`, holding the human's own 100 answers. Only the
sample workbook has one; real client data has no answer key.

**Agreement / net new** — the two numbers that matter, and they are different questions.
Agreement is how often we reproduce an answer the human filled in. Net new is how often we
fill in a row they left blank.

Neither number is a score out of the whole file, and neither means quite what it looks
like. **Net new is a measure of coverage, not of correctness**: a blank row has no answer
to check against, so any value we emit counts. And a row where the human answered and we
did not counts as **neither** agreement nor disagreement — declining to answer is a
different act from answering wrongly, and the arithmetic keeps them apart.

## Beyond the matcher

**Extraction** (`src/extraction/`) — the document-agnostic layer underneath the matcher.
`pdf_text.extract()` turns any PDF into page text and page tables; `spine/pdf.py`'s
statement parser is one consumer of that, not a replacement for it. A new document type
gets its own parser over the same primitive rather than its own PDF-reading code.

**Flag** (`src/checks/contract.py`) — one finding from the checking agent: a `check` name,
a `severity`, a `message` that reaches a fund manager verbatim, and the `source` it points
at. Deliberately shaped like **Field** — a flag with no citation is the unchecked output
the interview describes, so it never ships as a bare string either.

**Checking agent** (`src/checks/`) — runs after extraction, over already-structured
records, looking for internal inconsistency rather than resolving an unknown value. Not
the same job as the matcher: the matcher asks "what is this?", a check asks "does this
add up?". `footing.py`'s balance-continuity check is the first one, and the shape any
later check follows: `(records) -> list[Flag]`.

## Architecture vocabulary

See the `codebase-design` skill. In short: a **module** is deep when a lot of behaviour
sits behind a small **interface**; a **seam** is where that interface lives; an
**adapter** satisfies it. One adapter is a hypothetical seam, two is a real one.
