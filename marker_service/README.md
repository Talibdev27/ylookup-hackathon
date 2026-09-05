# Marker service

A one-endpoint HTTP wrapper around [Marker](https://github.com/datalab-to/marker), kept
entirely separate from the main app. Read this before touching it, and read
`src/extraction/marker_client.py` in the main repo for the other end of this.

## Why this is its own thing

Marker needs **Python 3.10+ and PyTorch**, plus several hundred MB of model weights. The
main app targets Python 3.9 (see its `AGENTS.md`) and runs as one lightweight worker on
Render's **free tier**, which does not have the memory to load PyTorch and Marker's
models at all. So this cannot be a module inside `src/` — it has to be a separate
process, with its own dependencies and its own, heavier deploy target.

The main app calls this service over plain HTTP when it wants Marker's extraction
quality instead of `pdfplumber`'s. If this service is not deployed or not configured, the
main app is completely unaffected — see `MARKER_SERVICE_URL` below.

## Run it locally

Needs Python 3.10+, and it will download several hundred MB of model weights the first
time `create_model_dict()` runs.

```bash
cd marker_service
python3.11 -m venv .venv && source .venv/bin/activate      # a separate venv from the main app
pip install -r requirements.txt
python app.py                                                # http://localhost:8080
```

```bash
curl -F "file=@/path/to/statement.pdf" http://localhost:8080/extract
```

## Deploy to Cloud Run

Requires the `gcloud` CLI, authenticated, with a GCP project that has billing enabled and
the Cloud Run and Cloud Build APIs turned on. Run this from inside `marker_service/`:

```bash
gcloud run deploy marker-service \
  --source . \
  --region europe-west2 \
  --memory 8Gi \
  --cpu 4 \
  --timeout 600 \
  --concurrency 1 \
  --min-instances 0 \
  --max-instances 1 \
  --allow-unauthenticated
```

Notes on those flags, because each one is a deliberate choice:

- **`--memory 8Gi --cpu 4`** — Marker's models need real memory. Too little and the
  container is OOM-killed partway through model loading, which looks like a silent
  crash rather than a clear error.
- **`--concurrency 1`** — one conversion at a time per instance. Marker's inference is
  heavy enough that letting two requests run concurrently on one instance risks the same
  OOM, not faster throughput.
- **`--timeout 600`** — a long, image-heavy PDF can take a couple of minutes on CPU.
  Cloud Run's default 5-minute timeout is close enough to this to be worth raising.
- **`--min-instances 0`** — scales to zero when idle, so it costs nothing between demos.
  The trade is a slow first request after any idle period: the container has to start
  and the model weights (baked into the image at build time — see the `Dockerfile`) have
  to load into memory, which is on the order of tens of seconds, not the multi-minute
  cold start you'd get if the weights were *not* baked in.
- **`--allow-unauthenticated`** — anyone with the URL can call this. Fine for a
  hackathon demo processing already-anonymised data; do not point it at anything
  sensitive without adding auth.

Deployment prints a service URL. Set that as `MARKER_SERVICE_URL` wherever the main app
runs (Render's environment variable settings, or locally via `export`) — see
`src/extraction/marker_client.py`.

## If Cloud Run fights you for more than it's worth

`--memory 8Gi` is the highest tier some Cloud Run regions or free-trial projects cap out
below. If deployment is rejected for exceeding a quota, either request a quota increase
(can take time you do not have this weekend) or fall back to running this locally on
whoever's laptop has the most RAM, exposing it with `ngrok` or Cloud Run's own
`gcloud run services proxy` for the duration of a demo. Marker is an enhancement to
extraction quality, not something the product depends on to function — `pdfplumber`
keeps working with this service turned off entirely.
