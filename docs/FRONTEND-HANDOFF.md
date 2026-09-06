# Stage D frontend handoff

Stage D exposes one review queue for matcher questions and automated inconsistency
findings. The existing page at `/` is the reference implementation. A separate frontend
can use the JSON routes below without reading files or reproducing queue logic.

This contract is intentionally about review work, not scoring. Matcher scores are not an
API field and should not be presented as live operational metrics.

## Routes

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Server-rendered review queue |
| `GET` | `/?all=1` | Queue including completed transactions |
| `GET` | `/api/review` | JSON review state, open items only |
| `GET` | `/api/review?all=1` | JSON review state including completed transactions |
| `POST` | `/rows/<row_id>/decide` | Save a matcher-field decision; existing route preserved |
| `POST` | `/api/flags/<flag_id>/decide` | Save an automated-flag decision |
| `GET` | `/export.csv` | Download every transaction with answers, findings and decisions |
| `GET` | `/upload` | Statement/workbook upload form |
| `POST` | `/upload` | Replace the workspace and run the pipeline |
| `POST` | `/reset` | Clear matcher and flag decisions for the current run |

## Review response

`GET /api/review` returns:

```json
{
  "summary": {
    "rows": 100,
    "automatically_settled_transactions": 12,
    "transactions_needing_matcher_review": 88,
    "matcher_questions_total": 376,
    "matcher_questions_remaining": 376,
    "automated_checks_total": 1,
    "automated_checks_executed": 1,
    "automated_checks_failed": 0,
    "automated_flags_found": 0,
    "automated_flags_remaining": 0,
    "total_review_items": 376,
    "total_review_items_remaining": 376,
    "transactions_remaining": 88,
    "reviewed_transactions": 0,
    "outstanding": 88,
    "reviewed": 0
  },
  "checks": {
    "checks_total": 1,
    "checks_executed": 1,
    "checks_failed": 0,
    "flags_found": 0,
    "completed": [
      {"check": "balance_continuity", "label": "Balance continuity", "status": "completed"}
    ],
    "failed": []
  },
  "items": [],
  "unattached_flags": []
}
```

The numbers above illustrate the bundled sample at the time of handoff; clients must
always render the values returned by the endpoint.

### Summary count definitions

| Field | Definition |
|---|---|
| `rows` | Total transactions in the current pipeline output |
| `automatically_settled_transactions` | Transactions that originally had neither matcher questions nor check flags |
| `transactions_needing_matcher_review` | Transactions with at least one matcher field whose status is not `auto` |
| `matcher_questions_total` | Individual non-auto matcher fields before reviewer decisions |
| `matcher_questions_remaining` | Matcher questions without a saved decision |
| `automated_checks_total` | Checks registered for this pipeline run |
| `automated_checks_executed` | Checks that completed, including checks that returned zero findings |
| `automated_checks_failed` | Checks that raised an exception |
| `automated_flags_found` | Findings produced by completed checks |
| `automated_flags_remaining` | Findings without a saved flag decision |
| `total_review_items` | Matcher questions plus automated flags |
| `total_review_items_remaining` | Unanswered matcher questions plus unhandled flags |
| `transactions_remaining` / `outstanding` | Transactions with at least one unanswered question or unhandled attached flag |
| `reviewed_transactions` / `reviewed` | Transactions that required review and are now fully handled |

A transaction with three open matcher questions counts as one transaction and three
review items. A transaction is not complete until all its matcher questions and all its
attached flags are handled. A document-level flag contributes to the review-item counts
but not to `transactions_remaining` because it has no related transaction.

## Review-item schema

Each member of `items` has this complete shape:

```json
{
  "transaction": {
    "row_id": 17,
    "source": {
      "pdf": "20260331_NI_V_SCSP_CALDER_EUR_030041.pdf",
      "page": 2
    },
    "raw": {
      "account_name": "NI V SCSP",
      "account_number": "240-644826-130",
      "currency": "EUR",
      "bank_reference": "10716RS62GWQ",
      "narrative_raw": "PAYMENT TO EXAMPLE",
      "narrative_normalised": "PAYMENT TO EXAMPLE",
      "value_date": "2026-03-05",
      "post_date": "2026-03-05",
      "credit": null,
      "debit": -301908.7,
      "balance": 20088.76
    }
  },
  "matcher_questions": [
    {
      "field": "matched_sender_beneficiary",
      "label": "Counterparty",
      "question": "Who was this actually paid to, or received from?",
      "value": "Example S.A.",
      "confidence": 0.62,
      "status": "needs_review",
      "evidence": {
        "span": [11, 20],
        "text": "The name matched more than one reference entry.",
        "source_list": "Vendor list"
      },
      "alternatives": [
        {"value": "Example Holdings S.A.", "confidence": 0.51}
      ],
      "decision": null
    }
  ],
  "automated_flags": [],
  "settled": false
}
```

`status` is `auto`, `needs_review`, or `unresolved`; only non-auto fields appear in
`matcher_questions`. When `?all=1` is used, `decision` may contain:

```json
{"choice": "manual", "value": "Corrected name"}
```

`choice` is `approve`, `alternative`, `manual`, or `unresolved`. An unresolved decision
has an empty final value and must not fall back to the rejected matcher proposal.

## Flag schema

An attached flag appears in `automated_flags`; a finding with no valid transaction row
appears once in the top-level `unattached_flags` array. Both use the same schema:

```json
{
  "flag_id": "3c0dcf53aaea934d15ec8628",
  "check": "balance_continuity",
  "label": "Balance continuity",
  "severity": "error",
  "severity_label": "Does not reconcile",
  "message": "The balance after this transaction should be 150.00, but the statement shows 200.00.",
  "source": {
    "pdf": "statement.pdf",
    "page": 2,
    "row_id": 17
  },
  "expected": 150.0,
  "actual": 200.0,
  "decision": null
}
```

`flag_id` is deterministic for the finding. Do not substitute an array index. Source
PDF values are filenames only; the API removes server filesystem paths. `expected` and
`actual` may be strings, numbers, lists, objects, or null for future checks.

When handled, `decision` has this shape:

```json
{
  "action": "resolved",
  "note": "The bank supplied a corrected statement.",
  "source": {"pdf": "statement.pdf", "page": 2, "row_id": 17},
  "decided_at": "2026-09-05T15:20:31.145922+00:00"
}
```

### Severity labels

| API severity | Display label |
|---|---|
| `info` | For information |
| `review` | Needs review |
| `error` | Does not reconcile |

Render `severity_label`, not the raw severity, as the primary wording. Do not display the
raw check name; render `label`. Unknown future values receive safe generic labels from
the backend.

## Decision requests

### Matcher field

`POST /rows/17/decide` accepts JSON or form data:

```json
{
  "choice": "approve",
  "field": "matched_sender_beneficiary",
  "value": "Example S.A."
}
```

For `manual`, a non-empty `value` is required. For `unresolved`, `value` is cleared.
Success returns HTTP 200 JSON for a JSON request. Invalid choices, blank manual values,
or a missing field return HTTP 400.

### Automated flag

`POST /api/flags/3c0dcf53aaea934d15ec8628/decide` requires JSON:

```json
{
  "action": "acknowledge",
  "note": "Optional reviewer note"
}
```

Allowed actions are:

- `acknowledge` — display “Acknowledged”
- `resolved` — display “Marked resolved”
- `false_positive` — display “Marked as not an issue”

The note is optional, trimmed, and limited to 1,000 characters. A valid request returns
HTTP 200:

```json
{
  "flag_id": "3c0dcf53aaea934d15ec8628",
  "action": "acknowledge",
  "note": "Optional reviewer note"
}
```

Malformed JSON, an invalid action, or an invalid note returns HTTP 400 without changing
state. An unknown flag ID returns HTTP 404 without changing state.

## Check execution states

Use `checks`, not `flags_found`, to decide whether checks ran:

- **Completed, zero findings:** `checks_executed > 0`, `checks_failed == 0`, and
  `flags_found == 0`. Say “No balance inconsistencies found.”
- **Completed with findings:** show the completed count and number of findings, then put
  each flag in its related transaction.
- **Failed:** `checks_failed > 0`. Say that one or more automated checks could not finish;
  keep matcher questions usable. The response exposes safe check labels, never exception
  messages or tracebacks.
- **Not run:** `checks_total == 0` and `checks_executed == 0`. Say checks have not run;
  do not present this as a clean result.

## Screen states

- **Loading:** preserve the page frame and use an announced busy state while fetching
  `/api/review`. Do not briefly show the empty or completed state.
- **No statements:** `summary.rows == 0`. Link to `/upload` and explain that statements
  and reference lists are required.
- **Open work:** `total_review_items_remaining > 0`. Group by transaction; render one
  card with separate “Answers to check” and “Inconsistencies found” sections.
- **Completed:** rows exist and `total_review_items_remaining == 0`. Confirm that every
  answer and inconsistency is handled and keep `/export.csv` available.
- **Request error:** retain the card and its entered note/correction, re-enable its
  controls, and display an inline error. Never optimistically remove work after a failed
  response.
- **Partial check failure:** keep the matcher queue available and show a non-technical
  check-status warning.

## Long content

Proposed positions and alternatives can be roughly 1,500 characters. Show a readable
preview around 220 characters with an ellipsis and an accessible disclosure such as
`<details><summary>Show full answer</summary>…</details>`. The submission value must be the
complete original string, not the preview. Use wrapping such as `overflow-wrap:anywhere`;
do not add a horizontally scrolling transaction card. Export already preserves the full
value.

## Source and evidence rendering

- Show the statement filename and page for every attached flag and transaction.
- Show the related transaction ID for a flag. An unattached flag must be presented as a
  document-level finding rather than silently dropped.
- `evidence.span` indexes `transaction.raw.narrative_raw`, never
  `narrative_normalised`. Validate bounds before highlighting in a non-Jinja frontend.
- Treat all narrative, messages, expected/actual values, notes and filenames as untrusted
  text. Escape them; never render them with raw HTML.
- Use `label`, `question`, `severity_label`, and the documented decision wording in the
  visible UI. Raw field and check identifiers are machine keys.

## Accessibility expectations

- Keep native buttons, inputs, textareas and disclosure controls keyboard operable.
- Give every textarea and manual-correction input an accessible label tied to its
  question or finding.
- Announce check status and save errors with an appropriate live/status region.
- Do not communicate severity or completion by colour alone; always pair it with text.
- Move focus to the next unanswered control only after a successful save.
- Preserve a visible focus indicator and a logical document order on narrow screens.

## Persistence and refresh behavior

Matcher decisions live in `data/decisions.json`; automated-flag decisions live in
`data/flag-decisions.json`. `data/flags.json` records both check execution status and
findings. The same findings are mirrored into `data/store.sqlite`, which also holds the
content-versioned upload/extraction history; the frontend does not access that database
directly. A successful upload/pipeline rebuild deletes both decision stores because row
IDs and findings may now refer to different transactions. The frontend should refresh
the entire review response after an upload.

## Intentionally out of scope

- The roadmap's 29-column DIU journal workbook
- New accounting checks without documented rules and fixtures
- Changes to Stage C matching or its scoring baseline
- Multi-user editing, authentication, a managed database, or concurrent workers
- A broad visual redesign of the existing review experience
- Exposing server filesystem paths, exception messages, or tracebacks
