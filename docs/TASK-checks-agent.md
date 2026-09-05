# Task · Checking agent — does this number foot to that number

The fund manager in Call 1, on why the review loop takes six or seven turns: *"nobody
reads it and asks whether this number foots to that number."* The matcher answers "what
is this row?"; the checking agent answers "does this add up?" — a different question,
and this is where it lives.

Read `AGENTS.md` and `CONTEXT.md` first, then `src/checks/footing.py` — it is short, real,
and the template for everything else here.

---

## Step 0 · Run the one that exists

```python
from src.checks import footing
from src.spine.build import STATEMENTS
from src.spine.pdf import parse_statements

flags = footing.check(parse_statements(STATEMENTS))
```

`tests/test_footing.py` proves two things: all 100 real transactions reconcile once put
back into chronological order (statements print newest-first — see the module docstring
before you assume the row order is wrong), and a deliberately broken balance gets caught.

**Done when** `python tests/test_footing.py` passes on your machine.

---

## Step 1 · A second deterministic check

Every check has the shape `(records) -> list[Flag]`, `Flag` defined in
`src/checks/contract.py`. Candidates that need no model, ranked by how directly they sit
under Call 1's complaint:

- **Cross-statement**: does an internal transfer leaving one account on the group's books
  arrive on another account for the matching amount? Two of the sample statements
  (`NI ABF I` and `NI ABF II`) already show one side each of the same Cephalus transfers.
- **Documented rule vs. actual data**: `matcher/stages.py`'s `cash_leg_transtype` already
  found one of these — the Process sheet's own booking rule contradicted 23 of the file's
  100 rows. A check that re-derives that finding generically, rather than as one matcher
  stage's side note, generalises past this one dataset.
- **Dataset 2**: `Movements Rec` in the loader workbook is the administrator's own
  pre-upload reconciliation sheet. A check that reproduces what it already flags, on the
  raw GL and loader data, is evidence the approach is not tuned to one file.

Pick one. Write the test before the check: know what a clean run and a broken run look
like on real data before writing the logic that tells them apart — `footing.py`'s test
does both.

**Done when** `./run-tests.sh` is green and the new check finds something real on the
bundled dataset (a genuine flag, not a synthetic one manufactured to pass the test).

---

## Step 2 · The judgement calls a rule cannot make

Not every inconsistency is arithmetic. "Does this classification make sense given the
narrative" needs the same kind of reading a human reviewer does. That is a model call, not
a rule, and it belongs behind the same `(records) -> list[Flag]` shape so the frontend
does not need to know which kind of check produced a given flag. Do not start here —
the deterministic checks are gradeable against real data today; a model call is not,
without deciding what "correct" means for it first.

**Done when** there is at least one worked example of a judgement-call check, with the
prompt and a sample flag it produced written into this file, even if it is not merged yet.
