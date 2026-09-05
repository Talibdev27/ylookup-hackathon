# TRUSS 1.0 — build log

Tracks decisions, gaps, and suggestions while building `docs/TRUSS.md` into working code.
Kept short by design — see git history / code for detail, not this file.

## Decisions made (not asked, logged here)

- **Location:** new `truss/` folder at repo root. Separate from the Python matcher
  (`src/`) — different product, same repo for now.
- **Stack:** Next.js (App Router) + TypeScript + Tailwind, per PRD §3.
- **Backend:** Next.js Route Handlers (`src/app/api/**`) over in-memory/JSON mock data —
  satisfies "implement with backend" (real HTTP endpoints, not just frontend mocks) without
  a second language/runtime. Matches the endpoint list in PRD §32.
- **Theme:** white ground, navy primary (per your instruction), restrained accent only for
  status colours (verified/needs-review/critical).
- **Scope for v1:** Investor Dashboard, Fund Manager Dashboard, Company Workspace
  (3-column: Recent Uploads / Spreadsheet / AI Agent), upload → mock-processing → result
  flow. Login is a stub (pick role, no real auth).

## Gaps / ambiguities in the PRD (flagging, not blocking)

- No data schema — inventing one (Investor, FundManager, Company, Document, FinancialLine)
  from the examples given.
- "AI Review" nav tab (§10) vs. the always-visible AI Agent panel (§16) overlap; treating
  the tab as a filtered/expanded view of the same issues, not a separate feature.
- No auth method specified — v1 has no real login, just a role switcher.
- No persistence requirement — mock backend is in-memory, resets on server restart.
- Excel export (§15) has no target format spec — v1 downloads a real `.xlsx` built from the
  mock rows, not a fake action.
- No error/empty states specified (zero companies, unsupported file type, upload failure) —
  adding minimal ones.

## Open questions (will ask if actually blocking)

- None yet.

## Suggestions

- Deployment/integration with the existing Python app's `render.yaml` is a separate decision
  for later — not needed to build or demo v1 locally.
