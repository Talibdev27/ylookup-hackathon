# W3 · Review UI

**Deliverable:** a reviewer clears 100 rows without ever opening Excel.

**Start now against a hand-written `data/rows.json` stub.** Do not wait for W1 or W2 —
the contract is fixed, and data arriving later changes nothing. If there is nothing
rendering within 90 minutes, this quarter of the score is already lost.

## Spec

The `Process` sheet in the client's own workbook is the spec — six stages, each with its
own review check, in their words. `src/ui/app.py` already maps stages to fields.

- **Exception-first.** Default view is `status != auto`. The 52 unresolved counterparties,
  the 30 rows with no project match and the 3 `Review` rows are the entire point.
- **Show the evidence.** Each field displays the proposal, its confidence, and the
  narrative with `evidence.span` highlighted. That is the "citation feature" the Process
  sheet already refers to.
- **Three actions:** approve, reject-and-pick-from-`alternatives`, correct manually.
- **Keyboard shortcuts** — `A` / `R` / `↓`. Someone clearing 52 exceptions with a mouse
  will hate you.
- **Progress header:** `48 auto · 31 reviewed · 21 remaining`.

## The bar

Judged by a non-technical fund manager, and the brief said "no AI slop". One screen, real
whitespace, one accent colour, tabular numbers right-aligned. Not a dashboard with six
chart widgets.

## Done when

Someone who has never seen the repo can clear the exception queue and export the result.
