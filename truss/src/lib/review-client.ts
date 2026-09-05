// Client-side calls to the real Python backend's review API (docs/FRONTEND-HANDOFF.md).
// Separate from backend.ts on purpose: everything in backend.ts runs server-side inside
// a Server Component, but the review tab needs live interactivity -- accept a proposal,
// acknowledge a flag, see the queue shrink -- which has to run in the browser. A browser
// fetch is subject to CORS, unlike a server-to-server one, which is why the Flask app's
// after_request hook allows cross-origin reads on /api/*.
//
// NEXT_PUBLIC_ prefix is required for Next.js to inline this into the client bundle;
// the plain BACKEND_URL in backend.ts would be undefined here.
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:5001";

export interface Evidence {
  span: [number, number] | null;
  text: string;
  source_list: string;
}

export interface MatcherQuestion {
  field: string;
  label: string;
  question: string;
  value: string | null;
  confidence: number;
  status: "needs_review" | "unresolved";
  evidence: Evidence;
  alternatives: { value: string; confidence: number }[];
  decision: { choice: string; value: string } | null;
}

export interface AutomatedFlag {
  flag_id: string;
  check: string;
  label: string;
  severity: "info" | "review" | "error";
  severity_label: string;
  message: string;
  source: Record<string, unknown>;
  expected: unknown;
  actual: unknown;
  decision: { action: string; note: string; decided_at: string } | null;
}

export interface ReviewItem {
  transaction: {
    row_id: number;
    source: { pdf?: string; page?: number };
    raw: {
      account_name?: string;
      currency?: string;
      narrative_raw?: string;
      credit?: number | null;
      debit?: number | null;
      value_date?: string;
    };
  };
  matcher_questions: MatcherQuestion[];
  automated_flags: AutomatedFlag[];
  settled: boolean;
}

export interface ReviewResponse {
  summary: {
    rows: number;
    total_review_items: number;
    total_review_items_remaining: number;
  };
  checks: {
    checks_total: number;
    checks_executed: number;
    checks_failed: number;
    flags_found: number;
  };
  items: ReviewItem[];
  unattached_flags: AutomatedFlag[];
}

export async function fetchReview(companyId: string): Promise<ReviewResponse | null> {
  try {
    const response = await fetch(
      `${BACKEND_URL}/api/review?all=1&company=${encodeURIComponent(companyId)}`,
      { cache: "no-store" }
    );
    if (!response.ok) return null;
    return (await response.json()) as ReviewResponse;
  } catch {
    return null;
  }
}

export async function decideMatcherField(
  rowId: number,
  field: string,
  choice: "approve" | "alternative" | "manual" | "unresolved",
  value = ""
): Promise<boolean> {
  const response = await fetch(`${BACKEND_URL}/rows/${rowId}/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ choice, field, value }),
  });
  return response.ok;
}

export async function decideFlag(
  flagId: string,
  action: "acknowledge" | "resolved" | "false_positive",
  note = ""
): Promise<boolean> {
  const response = await fetch(`${BACKEND_URL}/api/flags/${encodeURIComponent(flagId)}/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, note }),
  });
  return response.ok;
}
