# Task · README and submission

**Owner: the user.** The video is Firdavs's — `docs/TASK-demo.md`.

Deadline **Sunday 12:00**. Resubmission is allowed, so submit a working version at **11:00**
and improve it after. There is no reason to be submitting at 11:58.

---

## Step 1 · README

`README.md` carries the live URL, today's scoreboard, the Process-sheet finding and the
provenance table. Two things are left:

1. **Add the video link.** In the **Try it** section, directly under the Live bullet:
   `- **Video:** <link>`
2. **Follow your own README literally, from a clean clone.** Anything that needs a step the
   README does not mention is a bug — the judges said the minimum bar is a README plus one
   command they can execute.

```bash
git clone https://github.com/Talibdev27/ylookup-hackathon.git /tmp/readme-check
cd /tmp/readme-check && pip3 install -r requirements.txt && ./run.sh
```

Verified working on 5 September. Re-check after the last commit lands.

---

## Step 2 · Submit

Three things: the Tally form, the **public** GitHub repo, and the video link.

The repo has been public since 5 September. Confirm it still is — from a logged-out browser
window, not just this one:

```bash
gh repo view Talibdev27/ylookup-hackathon --json visibility
```

A private repo scores zero on the code-review criterion, which is 25%.

---

## Step 3 · Before anyone watches the live URL

<https://ylookup-hackathon.onrender.com/> is on Render's free tier: it sleeps after about
15 minutes and the first request then takes 30–60 seconds. **Open it once, a few minutes
before a judge or a demo touches it.**

Two things worth knowing about that instance:

- **An upload replaces the sample dataset for everyone**, and there is no in-app way back.
  The free tier's filesystem resets when the instance restarts, so it self-heals after a
  sleep, but a judge who uploads their own statements changes what the next judge sees.
- **A second, stale deployment exists** at `ylookup-review.onrender.com`, running a build
  from before the upload-feedback fix. Nothing links to it. Delete it in the Render
  dashboard so nobody lands on it.
- **Check the live site is on the last commit before you submit.** It has already been six
  commits behind once. The quick test: the top card should be the 29,700,000 EUR row. If it
  is the 0.44 bank charge, the deploy is stale — redeploy from the Render dashboard.

---

## Done when

The Tally form is submitted, the repo URL opens in a private browser window, and the video
plays from the link you pasted.
