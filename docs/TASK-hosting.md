# Task · Host it — Argha

The brief says hosting is optional and **earns extra points**. Nobody else is on it, so
this is the cheapest score left on the table.

Read `AGENTS.md` first. Work these steps in order; each ends on something you can check.

---

## Step 0 · Run it locally first

```bash
git clone https://github.com/Talibdev27/ylookup-hackathon.git
cd ylookup-hackathon
pip3 install -r requirements.txt
python3 serve.py        # http://127.0.0.1:5001
```

Without the dataset at `~/Downloads/Ylookup Hackathon Datasets/` you get **"No statements
loaded yet"** and an upload link — which is exactly what a judge will see on the deployed
URL, so it is the right thing to be looking at.

**Done when** the queue loads locally and you have clicked through `/upload`.

---

## Step 1 · What makes this different from a laptop

Three facts about this app that decide your deployment:

**It has no database.** State is files under `data/` — `rows.json`, `decisions.json`, and
whatever was uploaded into `data/workspace/`. On a platform with an ephemeral filesystem
every redeploy wipes them, and on more than one instance the two disagree. **Deploy a
single instance, and attach a persistent disk if the platform offers one.**

**It needs no dataset to boot.** The empty state is a working front door: a judge lands on
"No statements loaded yet", goes to `/upload`, and loads their own. That is the product
working, not a fallback.

**The dev server is not the production one.** `serve.py` runs Flask's own server, which
prints a warning telling you not to. `gunicorn` is in `requirements.txt`; the app object is
`src.ui.app:app`.

```bash
gunicorn 'src.ui.app:app' --bind 0.0.0.0:$PORT --workers 1 --timeout 120
```

**One worker, deliberately.** Uploads write files that the next request reads; a second
worker with its own filesystem view will serve a judge a half-loaded queue. `--timeout 120`
because reading a workbook takes a few seconds.

**Done when** `gunicorn` serves the app locally on a port you choose.

---

## Step 2 · Deploy

Any platform you already know. Render, Railway and Fly all take a repo, run the command
above and give you a URL — pick the one where you already have an account, because signing
up costs more time than deploying.

The app reads `PORT` from the environment, so the start command above works unmodified.
Nothing else needs configuring: no environment variables, no database URL, no secrets.

**Done when** the URL opens from your phone, on mobile data, showing "No statements loaded
yet".

---

## Step 3 · Load the demo data, and decide what is public

Two options, and this is a decision for the team rather than for you alone:

**(A) Leave it empty.** A judge uploads their own files. Nothing of the organisers' data
sits on a public URL. Safest, and it demonstrates the upload flow honestly.

**(B) Upload the sample workbook and statements once after deploying**, so the URL opens on
a populated queue. Better first impression, but it puts the organisers' anonymised client
data on a public address. They handed it out and their README calls it safe to distribute
— but publishing it to the open internet is a further step than being given it, so **ask
them in the event channel before doing it.** Do not commit the dataset to the repo either
way.

➡️ **Start with (A).** If the organisers say (B) is fine, it is a two-minute upload after
the fact.

**Done when** the URL is in a state you would be happy for a judge to open cold.

---

## Step 4 · Hand it over

Post the URL in the team channel and give it to Firdavs — the demo video should show the
hosted app, not localhost, and he needs to know before he records.

Add it to the top of `README.md`:

```markdown
**Live:** https://your-url-here
```

**Done when** the URL is in the README on `main` and Firdavs has it.

---

## If hosting fights you for more than 90 minutes

Stop and move to `matched_project_code` in `src/matcher/stages.py` — 100 rows filled, 30 of
them the literal string `Flag for review - no project match`. Hosting is worth extra points;
it is not worth an evening. Say so in the channel rather than going quiet.

---

## Two five-minute jobs, if you finish early

- **`src/journal/` is 35 lines of `NotImplementedError` that nothing imports.** Stage 6 was
  cut from scope. Delete the package — a reviewer reads it as abandoned work, and code
  review is 25%. The knowledge in it is already in `docs/ROADMAP.md`.
- **The repo is private and must be public before submission**, or the code-review score is
  zero: `gh repo edit Talibdev27/ylookup-hackathon --visibility public`. Coordinate with
  Firdavs so it happens once, deliberately.
