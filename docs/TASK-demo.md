# Task · Demo video, README, submission

Two of the four scoring criteria are decided here. Problem identification is *"did you
find a real problem in the interviews — and can you show us where it came from"*, and it
is 25% on its own. Product is another 25%, and the video is the only place the judges see
it working.

Read `AGENTS.md` first, then work these steps in order.

---

## Step 0 · Run it and write down today's numbers

```bash
git clone https://github.com/Talibdev27/ylookup-hackathon.git
cd ylookup-hackathon
pip3 install -r requirements.txt
./run.sh          # scoreboard, ~3 seconds
python3 serve.py  # review queue at http://127.0.0.1:5001
```

**Use the numbers `./run.sh` prints today, not the ones written below.** Mavlon is adding
columns while you work, so anything hardcoded here is already stale. As of writing:

- 7 statement PDFs, 4 currencies, **100 transactions**
- `matched_legal_entity` **100/100**, `cash_leg_transtype` **100/100**
- `matched_sender_beneficiary` **25 of the 48 the human matched**, plus **8 they left blank**
- **72 of 100** rows come back for review; **23** carry the cash-leg discrepancy

**Done when** you have a current scoreboard screenshot and the queue open in a browser.

---

## Step 1 · Write the script before you record

Three to five minutes. Four beats, roughly a minute each.

### Beat 1 — the problem, in their words (60s)

Open on the interview, because the first scoring criterion is literally whether you can
show where the problem came from. From `03-call-transcripts/call-1`, a fund manager on his
own administrator:

> "It took six or seven turns to get there. Nothing is ever right first time."

> "From a quality control perspective there just is not any... Frankly I no longer read
> what they send. I put it through an AI coding tool first, and it produced a forty-point
> memo of what was wrong."

Then the number that shows it is not just one grumpy client: **in the working file we were
given, 52 of 100 rows have no counterparty match at all.** Nobody resolved them. They
shipped.

### Beat 2 — the finding (60s)

This is the beat that separates you from every other team, so give it room.

Their `Process` sheet documents the rule: *"Cash - Received or Cash - Disbursed in the row
currency, matching the credit or debit side."* Every one of the 100 rows is booked
**Disbursed** — including the 23 where money came **in**.

Their own documented rule contradicts their own output, 23 times, in the file they
shipped. Show the tool finding it: the review queue, the flagged row, the reason in plain
English with the source cited.

That is Beat 1's quote made concrete — *"nobody reads it and asks whether this number foots
to that number"* — on their own data, in one run.

### Beat 3 — the product working (90s)

Screen-record, do not narrate slides.

1. **Upload.** Drag statements into `/upload`. It reads them and comes back with a queue.
   Say the reference lists are set up once and the weekly job is dropping in the PDFs.
2. **A row.** Show one card: what the bank wrote with the matched name highlighted, the
   account and page it came from, the proposal, the confidence in words, the reason.
   **Every claim on screen cites its source** — that is the "citation feature" their
   Process sheet asks for.
3. **Clearing it.** Accept with `A`. Take an alternative with `R`. On a row where the
   machine found nothing, type the right answer — the box suggests from their own
   reference lists. Say "I can't tell either" on one, and explain why that has to be a
   real answer.

### Beat 4 — how you know it works (30s)

The scoreboard. Two numbers per column, and say why they differ:

- **agreement** — how often we reproduce an answer the human filled in
- **net new** — how often we resolve a row the human left blank

Close on the honest version: *"Two columns are exact. The counterparty column agrees with
the human on N and resolves M they gave up on. Everything we are unsure about is in the
queue rather than hidden in a spreadsheet."*

**Done when** the script is written down with timings and you have said it out loud once.

---

## Step 2 · Record

Screen recording with voice-over. Read the script — improvising at 10am Sunday costs three
takes.

Practical: 1920×1080, browser zoom up so text is legible when compressed, close other
tabs, do a 20-second test recording and actually watch it before doing the full take.

**Done when** the file is 3–5 minutes, the audio is intelligible, and the text on screen is
readable at 720p.

---

## Step 3 · README

`README.md` already covers the problem, running it, provenance and layout. Your pass:

1. **Run `./run.sh` on a clean clone and follow your own README literally.** Anything that
   needs a step the README does not mention is a bug — the judges said the minimum bar is a
   README plus one command they can execute.
2. Put today's real scoreboard in it.
3. Add the demo video link. The README's **Try it** section already carries the live URL
   and today's scoreboard; add a `- **Video:** <link>` bullet directly under the Live one.

**Done when** someone who has never seen the repo can go from `git clone` to a running
review queue using only the README.

---

## Step 4 · Submit

Three things, per the brief: the Tally form, a **public** GitHub repo, and the video.

**The repo is already public** — verified 5 September. Check it still is, from a logged-out
browser window, before you submit: the code review is scored from it, and a private repo
scores zero on that 25%.

```bash
gh repo view Talibdev27/ylookup-hackathon --json visibility
```

Deadline is **Sunday 12:00**, and resubmission is allowed. Submit a working version at
**11:00** and improve it after if there is time; there is no reason to be submitting at
11:58.

**Done when** the Tally form is submitted, the repo URL opens in a private browser window,
and the video plays from the link you pasted.

---

## Two things that lose marks quietly

**Numbers that do not match the repo.** If the video says a number the scoreboard does not
print, a judge who runs `./run.sh` sees the difference. Re-record the scoreboard beat if
Mavlon lands a column after you film.

**Claiming more than it does.** Six of the ten columns are not written yet, and saying so
costs nothing — the honest version is stronger, because the whole product is an argument
for surfacing what the machine does not know.
