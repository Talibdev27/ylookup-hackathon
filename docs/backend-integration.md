# The TRUSS frontend, connected to the real backend

Four of TRUSS's pages are wired to the real Python matcher app instead of the mock
in-memory store `docs/truss1.0.md` documented: `truss/src/lib/backend.ts` (server-side
fetches), `truss/src/lib/review-client.ts` (client-side, for the interactive review
queue), and `truss/src/lib/upload-client.ts` (client-side, for real uploads — see
"Uploading" below). Everything else in `truss/` — investor/fund-manager dashboards for
the mock companies, the "AI Review" tab — is unchanged and still runs on its own mock
data. Nothing here removes or breaks that; a page checks the real backend first and
falls back to the mock store if the company isn't one of the four real funds.

## Run both sides

```bash
# Terminal 1 -- the Python matcher app
cd ylookup-hackathon
./run.sh          # or: python3 -m src.pipeline
python3 serve.py  # http://127.0.0.1:5001

# Terminal 2 -- the frontend
cd ylookup-hackathon/truss
npm install
npm run dev        # http://localhost:3000
```

Then open `http://localhost:3000/company/nordvik-infrastructure-v-scsp` (or any of the
other three ids `GET /api/companies` returns) for the four real funds' balance sheet,
income statement, cash flow, and review queue tabs.

## What's wired, and how

**`GET /api/companies`, `.../balance-sheet`, `.../income-statement`, `.../cash-flow`**
(`src/reports/statements.py`, `src/ui/app.py`) — the balance sheet and income statement
pages fetch these server-side, in the page's own Server Component, and map the response
into TRUSS's `FinancialStatement` shape. No CORS involved: a Next.js Server Component
runs on the Node server, not the browser, so a fetch from it to Flask is a plain
server-to-server call. Cash flow deliberately returns `available: false` with a reason —
see `docs/analyst-flags.md` for why building this needs a real mapping decision the
data does not supply on its own, not a rollup like the other two.

**`GET /api/review?company=<id>`, `POST /rows/<id>/decide`,
`POST /api/flags/<flag_id>/decide`** (`src/ui/app.py`) — the new "Review Queue" tab
(`truss/src/components/ReviewQueue.tsx`) is a client component: it needs live
interactivity (accept a proposal, acknowledge a flag, watch the queue shrink), which has
to run in the browser, not the Next.js server. A browser fetch is subject to CORS,
unlike a server-to-server one, which is why `src/ui/app.py` has an `after_request` hook
allowing cross-origin reads on `/api/*` specifically.

## Uploading

**`POST /api/upload`, `POST /api/gl-migration/upload`** (`src/ui/app.py`) — the
"Documents" tab (`truss/src/components/BackendUpload.tsx`, via
`truss/src/lib/upload-client.ts`) is a client component for the same reason the review
queue is: the file picker lives in the browser. Both routes are JSON siblings of the
plain-Flask `/upload` and `/gl-upload` pages — same validation and processing
(`_process_statement_upload` / `_process_gl_upload` in `src/ui/app.py`), but a JSON
response instead of a redirect, since a fetch() caller wants a result to render, not a
page to follow. Covered by the same `/api/*` CORS prefix as the review queue; a
multipart/form-data POST with no custom headers is a CORS-safelisted "simple request"
regardless, so no preflight is even involved.

Uploads here are dataset-wide, not scoped to the company whose Documents tab they were
opened from: the reference workbook and statements cover every fund the matcher knows,
and the GL/loader pair is a separate dataset entirely. `companyId` is only used to link
back to that company's own Review Queue tab afterward. For a mock company (not one of
the four real funds), the Documents tab keeps the original mock `UploadDropzone` /
`DocumentsBrowser` flow, which posts to this app's own `/api/documents/upload` route and
returns fabricated data — see that route's own comment for why.

## Company ids

`Company.id` for the four real funds is the Python backend's own `slugify(legal entity
name)`, hardcoded in `truss/src/lib/mock-data.ts` as `NORDVIK_FUND_IDS` rather than
fetched at build time, to keep `getCompany()` (used synchronously all over the mock
store) working unchanged. **If `_slug()` in `src/ui/app.py` ever changes, these four ids
have to change with it** — there is no test pinning that the two sides agree, since
they are two different codebases; this is the one manual coupling to remember.

## Environment variables

| Variable | Used by | Default |
|---|---|---|
| `BACKEND_URL` | `truss/src/lib/backend.ts` (server-side) | `http://localhost:5001` |
| `NEXT_PUBLIC_BACKEND_URL` | `truss/src/lib/review-client.ts`, `truss/src/lib/upload-client.ts` (client-side) | `http://localhost:5001` |

Two separate variables because they run in two different places: `BACKEND_URL` never
needs the `NEXT_PUBLIC_` prefix since it is only ever read on the server, and giving it
that prefix would needlessly expose it to the client bundle.

## What this does not do

- Does not touch the mock investor/fund-manager dashboards' own company list, beyond
  adding the four real funds to it so they are navigable and `getCompany()` finds them
  (see `NORDVIK_FUND_IDS` in `mock-data.ts`). `investmentValueGbp` for these four is `0`
  rather than an invented figure — the matcher data is transaction activity, not a
  committed-capital number.
- Does not change the "AI Review" tab or the Excel export button on any page — those
  still use the mock store and are unrelated to this. The document-upload flow *is* now
  real for the four real funds (see "Uploading" above); it stays mock for every other
  company.
- Does not add authentication, retries, or a loading skeleton beyond a spinner and a
  plain "could not reach the backend" message. Good enough to demo; not production
  hardening.
