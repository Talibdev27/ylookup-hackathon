// The real Python matcher app -- a separate server on its own origin, not the mock
// Route Handlers under src/app/api/**. See docs/backend-integration.md for what each
// endpoint returns and why the three financial statement pages are wired here while
// investor/fund-manager/document upload stay on the mock store for now.
//
// BACKEND_URL is a plain (non-NEXT_PUBLIC_) env var on purpose: every call in this file
// runs server-side, in a Server Component or a Route Handler, never in the browser, so
// it never needs to be exposed to client bundles. Defaults to the Flask dev server.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:5001";

export interface BackendCompany {
  id: string;
  name: string;
}

export interface BalanceSheet {
  legal_entity: string;
  period: string;
  assets: number;
  liabilities: number;
  capital: number;
  ties: boolean;
}

export interface IncomeStatement {
  legal_entity: string;
  period: string;
  revenues: number;
  expenses: number;
  net_income: number;
}

export interface CashFlowUnavailable {
  legal_entity: string;
  available: false;
  reason: string;
}

async function get<T>(path: string): Promise<T | null> {
  try {
    // no-store: this is live matcher/ledger data, not something Next.js should cache
    // across requests the way it would a static page.
    const response = await fetch(`${BACKEND_URL}${path}`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    // The Flask app is not running, or not reachable from here. Every caller treats
    // null the same way it treats "no data yet" -- an honest empty state, not a crash.
    return null;
  }
}

export function fetchCompanies() {
  return get<{ companies: BackendCompany[] }>("/api/companies").then((r) => r?.companies ?? []);
}

export function fetchBalanceSheet(companyId: string) {
  return get<BalanceSheet>(`/api/companies/${companyId}/balance-sheet`);
}

export function fetchIncomeStatement(companyId: string) {
  return get<IncomeStatement>(`/api/companies/${companyId}/income-statement`);
}

export function fetchCashFlow(companyId: string) {
  return get<CashFlowUnavailable>(`/api/companies/${companyId}/cash-flow`);
}
