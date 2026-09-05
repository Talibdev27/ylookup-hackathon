# Working in this repo

Bank statements in, reviewable journal entries out, with a fund manager checking whatever
the matcher was unsure about. `README.md` covers what it is and how to run it.

## Orient

- `CONTEXT.md` — the domain words. Read it before naming anything.
- `CONTRACT.md` — the row shape every part of the system passes around.
- `docs/TASK-*.md` — a self-contained brief per open piece of work. Start at the one you
  were handed.

## The loop

```bash
./run.sh          # pipeline + scoreboard. This is the feedback loop.
./run-tests.sh    # every suite, exits non-zero on the first failure
python3 serve.py  # the review queue, http://127.0.0.1:5001
```

`./run.sh` prints the scoreboard: per column, how often we reproduce an answer the human
filled in, and how often we resolve a row they left blank. **The scoreboard is the
arbiter.** Run it after every change. A change that lowers a number gets reverted, however
convincing the reasoning was — `complete()` in `src/matcher/counterparty.py` records three
versions measured against each other, and the one that looked best scored worst.

## Conventions the code will not tell you

**Every field carries its evidence.** A stage returns a `Field` with a value, a
confidence, a status, and an `Evidence` saying where the answer came from. A value with
no provenance cannot be reviewed, and being reviewable is the product.

**`evidence.text` reaches a fund manager verbatim.** Write it the way you would say it to
an accountant: *"'CHARGES FOR 2' is not on any of the reference lists"*. Field names,
tracebacks and confidence floats stay on the console. `src/ui/labels.py` holds every word
the screen shows, so wording changes land there rather than in templates.

**`unresolved` is a good answer.** Say so when the machine cannot tell, and carry the near
misses as `alternatives`. A confident wrong value is the failure this product argues
against — the fund manager in the interviews stopped trusting output nobody checked.

**Where the docs and the data disagree, the data wins, and the disagreement is worth
surfacing.** The client's `Process` sheet describes rules their own working file breaks in
23 places. Reproducing the data keeps the output loadable; flagging the difference is the
demo.

**Spans index the raw narrative.** `evidence.span` is a character offset into
`narrative_raw`, because that is the text highlighted on screen. `normalise()` returns an
index map for exactly this.

## Adding a matcher stage

One shape, `(row, lists) -> Field`, in `src/matcher/stages.py`. Write the function, add a
line to `REGISTRY` in the same file, run `./run.sh`. `matched_legal_entity` and
`cash_leg_transtype` are short, implemented, and show the conventions.

Registry order is the order stages run, and it is load-bearing: a stage reads what earlier
stages wrote via `row.fields`. `tests/test_stages.py` pins the one real constraint.

A stage that is not written yet raises `NotImplementedError`. Anything else it raises is
treated as a defect: the run says so loudly and the row comes back as `unresolved`.

## Before you push

`./run-tests.sh` green, and the scoreboard the same or better. Add a test beside the
behaviour you changed — `tests/test_stages.py` has a three-line fake `ReferenceLists`, so
testing a stage needs no workbook.
