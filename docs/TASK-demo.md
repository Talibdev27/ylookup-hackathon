# Task · The demo video

**Owner: Firdavs.** The README and the Tally submission are the user's — you only need to
film. You do not need to read any code to do this, and you do not need repo access.

Two of the four scoring criteria are decided here. *Problem identification* is 25% on its
own and is literally *"did you find a real problem — and can you show us where it came
from"*. *Product* is another 25%, and this video is the only place a judge sees it running.

**Target: 3 minutes 30.** One take, read from the script below.

---

## The one-line pitch

> **Watch it catch something the administrator already shipped.**

Not "watch it save twenty minutes". Resist that framing even though it sounds punchier —
the app tells you on screen that 88 of 100 rows still need a human, so a speed claim
invites a question the build cannot answer. What it *can* prove is that it finds errors in
a file that was already delivered and signed off. Nobody else will have that.

---

## Step 0 · Get it running

```bash
git clone https://github.com/Talibdev27/ylookup-hackathon.git
cd ylookup-hackathon
pip3 install -r requirements.txt
./run.sh          # scoreboard, ~3 seconds
python3 serve.py  # the review queue at http://127.0.0.1:5001
```

**Film against localhost, not the deployed site.** The live instance sleeps and takes
30–60 seconds to wake, which will eat a take.

**Read this before you touch the upload screen.** Uploading replaces the sample dataset
and there is no button to put it back — `/reset` only clears your decisions. If you upload
and then want the sample again:

```bash
rm -rf data/workspace
```

Uploaded data also has no answer key, so **the scoreboard stops working until you do
that**. Simplest safe order: film everything else first, film the upload beat last.

**Done when** `./run.sh` prints a scoreboard and the queue opens in a browser.

---

## Step 1 · The numbers, checked on the day

Say only numbers that `./run.sh` prints on the day you film. If a judge runs it and gets
something different, that is a quiet mark against you. As of 5 September:

- 7 statement PDFs, 4 currencies (EUR, GBP, USD, DKK), **100 transactions**
- **88 of 100** rows come back for checking; **12** needed none
- **23** rows carry the cash-leg contradiction
- `matched_legal_entity` **100/100** · `cash_leg_transtype` **100/100**
- **Counterparty** — the hardest column — **45** of the 48 the human matched, plus **8 they
  left blank**, and **zero disagreements**: the three it does not reproduce, it declines
- **Seven** disagreements across all ten columns put together

---

## Step 2 · The script

Four sections. The middle three are the three things the judges need to see: **it reads
the statements**, **it shows its evidence**, **a person corrects it fast**.

### 0:00–0:45 · The problem, in their words

Open on the client's own spreadsheet, not the app.

> "This is a fund administrator's working file. A hundred bank transactions that somebody
> turned into journal entries by hand."

Scroll the counterparty column so the blanks are visible.

> "Fifty-two of these hundred rows have no counterparty at all. Nobody worked out who the
> money went to. This file was delivered."

Then the interview quote, on screen as text:

> "From a quality control perspective there just is not any. Frankly I no longer read what
> they send. I put it through an AI coding tool first, and it produced a forty-point memo
> of what was wrong."

Then the line that is the whole project, from the same call:

> "Which raises the question of whether I should be building software to check my own fund
> administrator."

> "He said that. We built it."

One more, because it decides what you claim later:

> "As a user I am not sensitive to whether a turn took them an hour or forty-eight hours.
> What I care about is the count of turns."

> "So this is not about being fast. A turn gets spent when something comes back wrong. This
> shows its work on every number, so there is less to come back."

### 0:45–1:25 · One: it reads the statements

Cut to the upload screen. Drag the seven PDFs in. Press **Read the statements**.

> "This week's bank statements go in as PDFs. The reference lists — their funds, related
> parties, investors, suppliers, deals — are set up once and stay put, so the weekly job is
> just dropping in the statements."

While it works:

> "Seven statements, four currencies, a hundred transactions. It pulls out every payment,
> and then ten stages work through the same questions their own process document asks."

Land on the queue. Read the header aloud:

> "Eighty-eight need a human look. Twelve it was confident enough to fill in and leave
> alone. It leads with the ones worth your attention first."

### 1:25–2:35 · Two: it shows its evidence — and what it found

You are now on the first card: **NI V SCSP, money in, €29,700,000**. Do not scroll past it.

> "Top of the queue. Twenty-nine point seven million euros in."

Point at **What the bank wrote**, and the line under it naming the PDF and page.

> "That is the raw bank text, and underneath it the statement file and the page it came
> from. Every single claim on this screen says where it came from — that is the whole
> point."

Now scroll to the question **How should the cash side be booked?** and read the reason
verbatim. This is the most important fifteen seconds of the video — slow down.

> "Their own process document says a credit — money coming in — books to Cash Received.
> Every row in the file they shipped is booked Cash Disbursed. Including this one.
> Including twenty-three of them."

> "Their documented rule, contradicted by their own output, twenty-three times, in the
> file they delivered. It found that in one run, and it cites the process sheet and the
> stage. That is exactly the thing the fund manager said nobody checks."

### 2:35–3:20 · Three: a person clears it in seconds

Scroll to the **fourth card** — *NORDVIK INFRASTRUCTURE ADVANCED, INTERNAL TRANSFER*, money
in, **€6,550,000**. Use this card. It carries every claim the product makes, on one screen,
with no scrolling.

> "Here is the ordinary case."

**Who was this actually paid to** proposes `Nordvik Infrastructure Advanced Bioenergy Fund
II SCSp`, *fairly confident*, because the bank text names 'NORDVIK INFRASTRUCTURE ADVANCED'.
Open the alternatives and let the judges see them — **three near-identical fund names**,
differing only by suffix: *Fund I SCSp*, *Fund I DK A K/S*, *Fund II QFPF SCSp*.

> "The bank wrote one name. Four funds in their own list start with it, and they differ by a
> suffix. It picks the closest, shows the reason, and puts the other three one keypress
> away — because this is exactly the call a person should be making, not a machine."

Then use the keyboard, deliberately, one key at a time:

> "Accept — `A`." *(press A)*
> "Or take one of the alternatives — `R`." *(press R)*
> "Or type your own, and it suggests from their own reference lists — `E`." *(press E, type a
> few letters, show the suggestions)*

Now point at the three questions on the same card reading **"Could not work this out"** —
no project named in the text, so no deal, so no position — and press `U` on one.

> "And these it cannot answer. The bank text names no project, so there is no deal, so there
> is no position. It says so, and 'I can't tell either' is a real answer you can record.
> That matters more than it sounds: a confident wrong number is the thing that made him stop
> reading what they send."

Hit **Download as a spreadsheet**, open it, point at the column saying who decided each
answer.

> "Out comes the file, and every answer carries who decided it — the machine or the person."

### 3:20–3:45 · Close on the honest version

Cut to the terminal, `./run.sh`.

> "Two columns match the human exactly, a hundred out of a hundred. The counterparty column
> — the one they gave up on fifty-two times — agrees with them on forty-five, resolves eight
> they left blank, and disagrees on nothing. Seven disagreements across all ten columns.
> Everything we are unsure about is in the queue, where somebody can see it — instead of
> blank in a spreadsheet nobody reads."

Stop there. Do not add a features list.

---

## Step 3 · Record it properly

- 1920×1080. Browser zoom up so the text is legible after compression.
- Close other tabs. Turn off notifications.
- **Do a 20-second test recording and actually watch it back** before the full take.
  Check you can hear yourself and read the screen.
- Read the script. Improvising at 10am Sunday costs three takes.

**Done when** the file is 3–4 minutes, the audio is intelligible, and the on-screen text is
readable at 720p.

---

## Two things that lose marks quietly

**A number the repo does not print.** If you say a figure `./run.sh` disagrees with, a judge
who runs it sees the difference. Re-check Step 1 on the day.

**Claiming more than it does.** Say plainly that 88 rows go to a human. The honest version
is stronger here, because the entire product is an argument for surfacing what the machine
does not know.
