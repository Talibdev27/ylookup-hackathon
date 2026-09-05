# Task · Front door — beyond the review queue

`src/ui/` already is the frontend for one workflow: upload statements, work the queue.
The platform needs a front door in front of that — the place an investor or fund manager
lands, uploads whatever they have, and sees what came back, whether that is a matcher
queue or a list of flags from `src/checks/`. This is not a rewrite: it extends `src/ui`,
because `docs/TASK-hosting.md` already commits the team to one Flask app, one instance,
file-backed state, and that decision should not get re-litigated for a second UI.

Read `AGENTS.md` and `src/ui/app.py` first — the existing upload flow and its error
handling are the pattern to repeat, not replace.

---

## Step 0 · What "no AI slop" is actually asking for

UI is 25% of the score, scored on a non-technical fund manager using it. The existing
`review.html` already follows the rule that matters most: no field keys, no confidence
floats, no raw currency codes on screen — `src/ui/labels.py` is the one place wording
lives. Whatever this task adds should read the same way. Look at the current screen
before designing a new one; consistency reads as considered, a second visual language
reads as two different hackathon side-projects glued together.

**Done when** you can point at one existing screen and say which part of the new one
copies it on purpose.

---

## Step 1 · The landing page

One screen, before the upload form: what this is, in the fund manager's or investor's own
words, not "an agentic pipeline for document reconciliation." Say what happens to what
they upload and why — Call 1's fund manager stopped trusting output nobody checked, so
say plainly that a human still reviews anything the machine is unsure about, because
overclaiming certainty is the exact failure this product argues against.

**Done when** someone who has never seen this project can read the landing page and
correctly guess what the upload button does before clicking it.

---

## Step 2 · A flags view, next to the queue

`src/checks/` produces `Flag` objects — `check`, `severity`, `message`, `source`. The
review queue already renders something structurally similar (a row, a reason, a source);
do not invent a second visual pattern for a flag when the queue's row card already
solves "here is a finding, here is why, here is where it came from." Reuse the template
partial rather than writing a new one from scratch.

**Done when** a flag from `footing.py` (or whatever Step 1 of
`docs/TASK-checks-agent.md` produced) renders on screen with its message and source,
using the existing row-card markup.

---

## Step 3 · One upload flow, more than one document type

Today's `/upload` accepts statements and a reference workbook, by name. Extending it to
a second document type means the form and the error messages need to say which kind of
file goes where — `src/ui/app.py`'s existing validation (wrong extension, missing
workbook) is the model: fail with a specific, plain-English reason, not a stack trace.

**Done when** uploading the wrong file type for a given slot gives the same quality of
error message the statement upload already does.

---

## If this fights you for more than the time it is worth

The existing review queue is a working, scored product on its own. A polished front door
around it is worth real UI points; a half-built second flow that leaves both screens
looking unfinished is not. Say so in the channel rather than shipping two incomplete
things instead of one complete one.
