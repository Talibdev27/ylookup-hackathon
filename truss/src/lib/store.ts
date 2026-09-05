import {
  analysisByDocumentId,
  companies,
  documents,
  fundManagers,
  investors,
  statementsByDocumentId,
} from "./mock-data";
import type { AiAnalysis, Document, DocumentStatus, FinancialStatement } from "./types";

// A process-lifetime in-memory store standing in for a real backend. State resets on
// server restart — see docs/truss1.0.md, this is a logged, deliberate v1 gap.
//
// Kept on `globalThis` rather than a plain module-level const: Next.js bundles each
// route handler and each page separately, so a plain `const` gets re-initialised per
// bundle and an upload made via one route would silently not be visible from another.
// `globalThis` is the one thing guaranteed to be the same object across all of them in
// a single server process.

type StoreState = {
  investors: typeof investors;
  fundManagers: typeof fundManagers;
  companies: typeof companies;
  documents: Document[];
  statements: Record<string, FinancialStatement>;
  analysis: Record<string, AiAnalysis>;
};

const globalForStore = globalThis as unknown as { __trussStore?: StoreState };

const state: StoreState =
  globalForStore.__trussStore ??
  (globalForStore.__trussStore = {
    investors: [...investors],
    fundManagers: [...fundManagers],
    companies: [...companies],
    documents: [...documents],
    statements: { ...statementsByDocumentId },
    analysis: { ...analysisByDocumentId },
  });

export function listInvestors() {
  return state.investors;
}

export function getInvestor(id: string) {
  return state.investors.find((i) => i.id === id);
}

export function listCompaniesForInvestor(investorId: string) {
  const investor = getInvestor(investorId);
  if (!investor) return [];
  return state.companies.filter((c) => investor.companyIds.includes(c.id));
}

export function listFundManagers() {
  return state.fundManagers;
}

export function listCompanies() {
  return state.companies;
}

export function getCompany(id: string) {
  return state.companies.find((c) => c.id === id);
}

export function listDocumentsForCompany(companyId: string) {
  return state.documents
    .filter((d) => d.companyId === companyId)
    .sort((a, b) => (a.uploadedAt < b.uploadedAt ? 1 : -1));
}

export function getDocument(id: string) {
  return state.documents.find((d) => d.id === id);
}

export function getLatestDocumentOfKind(companyId: string, kind: Document["statementKind"]) {
  return listDocumentsForCompany(companyId).find((d) => d.statementKind === kind);
}

export function getStatement(documentId: string) {
  return state.statements[documentId];
}

export function getAnalysis(documentId: string): AiAnalysis {
  return (
    state.analysis[documentId] ?? {
      documentAnalysed: true,
      numbersExtracted: true,
      previousPeriodCompared: false,
      issues: [],
      suggestions: [],
    }
  );
}

export function setDocumentStatus(id: string, status: DocumentStatus, reviewedBy?: string) {
  const doc = state.documents.find((d) => d.id === id);
  if (!doc) return undefined;
  doc.status = status;
  if (reviewedBy) {
    doc.reviewedBy = reviewedBy;
    doc.reviewedAt = new Date().toISOString();
  }
  return doc;
}

export function createUploadedDocument(input: {
  companyId: string;
  name: string;
  sourceFormat: Document["sourceFormat"];
  statementKind: Document["statementKind"];
}): Document {
  const doc: Document = {
    id: `doc-upload-${crypto.randomUUID()}`,
    companyId: input.companyId,
    name: input.name,
    statementKind: input.statementKind,
    sourceFormat: input.sourceFormat,
    uploadedAt: new Date().toISOString().slice(0, 10),
    status: "processing",
    aiConfidence: 0,
    sourceFileNote: input.name,
  };
  state.documents.unshift(doc);
  return doc;
}

const STATEMENT_METRICS: Record<Document["statementKind"], string[]> = {
  balance_sheet: ["Cash", "Receivables", "Total Assets", "Liabilities", "Equity"],
  income_statement: ["Revenue", "Operating Expenses", "Net Income"],
  cash_flow: [
    "Opening Cash",
    "Net Cash from Operations",
    "Net Cash used in Investing",
    "Net Cash from Financing",
    "Closing Cash",
  ],
};

/**
 * Fills in a document's structured data and AI analysis once "processing" completes.
 * Figures are generated, not extracted — there is no real OCR/LLM backing this yet
 * (docs/truss1.0.md). Real, plausible-looking numbers so the spreadsheet/AI panel have
 * something to show for the demo.
 */
export function finishProcessing(documentId: string): Document | undefined {
  const doc = state.documents.find((d) => d.id === documentId);
  if (!doc) return undefined;

  const current = `Period ending ${doc.uploadedAt}`;
  const previous = "Prior period";
  const metrics = STATEMENT_METRICS[doc.statementKind];
  const base = 200000 + Math.round(Math.random() * 800000);

  const lines = metrics.map((metric, i) => {
    const prevVal = Math.round(base * (0.85 + i * 0.05));
    const curVal = Math.round(prevVal * (0.95 + Math.random() * 0.2));
    return { metric, values: { [current]: curVal, [previous]: prevVal } };
  });

  state.statements[documentId] = { kind: doc.statementKind, periods: [current, previous], lines };

  const flagged = Math.random() < 0.4;
  state.analysis[documentId] = {
    documentAnalysed: true,
    numbersExtracted: true,
    previousPeriodCompared: true,
    issues: flagged
      ? [
          {
            id: `issue-${documentId}-1`,
            title: `${lines[0].metric} moved sharply`,
            detail: `${lines[0].metric} changed more than expected versus the prior period. Review supporting documentation.`,
            severity: "warn" as const,
          },
        ]
      : [],
    suggestions: flagged
      ? ["Compare against the previous period", "Confirm the underlying source document"]
      : ["No unusual movement detected"],
  };

  doc.aiConfidence = 0.9 + Math.random() * 0.09;
  doc.status = flagged ? "needs_review" : "verified";
  return doc;
}
