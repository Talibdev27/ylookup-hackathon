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

**Row** — one transaction on its way to becoming a journal entry. Carries the raw
statement values and a **Field** per column the matcher fills.

**Field** — one answer about a row: a value, a confidence, a status (`auto`,
`needs_review`, `unresolved`), the **Evidence** it came from, and the alternatives that
were rejected. Never a bare string: a value with no provenance cannot be reviewed.

**Evidence** — where a value came from. A span into the narrative, the reference list it
was found in, and a plain-English reason. Rendered verbatim to a fund manager, so it is
written in their language and never carries technical detail.

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
Agreement is how often we reproduce an answer the human filled in. Net new is how often
we resolve a row they left blank.

## Architecture vocabulary

See the `codebase-design` skill. In short: a **module** is deep when a lot of behaviour
sits behind a small **interface**; a **seam** is where that interface lives; an
**adapter** satisfies it. One adapter is a hypothetical seam, two is a real one.
