# 1. Trust the data over the Process sheet

Status: accepted · 5 September 2026

## Context

The client's workbook carries a `Process` sheet: their own stage-by-stage guide to the
work, with the review checks for each stage. It is the closest thing to a specification we
were given, and the review queue's layout is built from it.

In three places it describes rules the client's own working file does not follow.

**The cash leg.** The sheet says *"Cash - Received or Cash - Disbursed in the row currency,
matching the credit or debit side."* All 100 rows are booked `Cash - Disbursed`, including
the 23 where money came in.

**The classification vocabulary.** The sheet says the values are Investment / Vendor /
Related Party / Investor / Internal / Review. The data has no `Investor` at all, and adds
`Other` (32 rows) and `Investment Transfer` (15).

**The project code.** The sheet describes a lookup against the project code report. 30 of
100 rows instead carry the literal string `Flag for review - no project match`.

Every stage that touches these had to pick a side.

## Decision

**Reproduce the data. Surface the disagreement.**

A stage emits the value the working file actually contains, so its output stays loadable
by the target system. Where the documented rule would have produced something different,
the row is flagged `needs_review` with the difference stated in the evidence, and the
reviewer decides.

## Consequences

**The output stays usable.** Following the sheet would have produced `Cash - Received` on
23 rows that the target system has never seen booked that way.

**The disagreement becomes the product.** The interview these datasets exist to answer is
a fund manager describing exactly this gap — *"nobody reads it and asks whether this number
foots to that number"* — and the tool now finds an instance of it in the administrator's
own file, in one run. That is a stronger demonstration than either being "correct" against
the sheet or silently agreeing with the data.

**It costs the appearance of correctness.** A reader comparing the code to the Process
sheet will find them disagreeing on purpose. This document is the answer to that.

**It could be wrong.** The sheet may be current and the working file stale, in which case
we are reproducing three errors rather than one specification. We accepted that: the file
is what the target system received, and a reviewer sees the alternative on every affected
row and can pick it.

## Alternatives considered

**Follow the Process sheet.** Defensible, and produces output the target system would
reject on 23 rows. It also throws away the finding.

**Follow the data silently.** Simpler, scores identically against the ground truth, and
loses the only thing in this build that a fund manager would find surprising.
