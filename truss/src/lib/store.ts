import "server-only";
import {
  analysisByDocumentId,
  companies,
  documents as seedDocuments,
  fundManagers,
  investors,
  statementsByDocumentId,
} from "./mock-data";
import { db, misconfiguration } from "./db";
import type { AiAnalysis, Document, DocumentStatus, FinancialStatement } from "./types";

/**
 * Documents and what was extracted from them, in Postgres.
 *
 * This used to be an object held for the lifetime of the process. That survives `next
 * dev`, which is one process, and does not survive Vercel, where each route is its own
 * serverless function: the upload POST wrote into one lambda's memory and the page render
 * that followed read a different lambda, which had never heard of the document. An upload
 * that visibly succeeded 404ed a second later.
 *
 * Two kinds of data live here and only one of them is in the database.
 *
 * *Reference data* -- investors, fund managers, companies -- is fixed seed data in
 * `mock-data.ts`. Nothing writes it at runtime, so it stays in code where it can be read
 * without a round trip.
 *
 * *Documents* are seeded in code too, but they can be uploaded and reviewed, so anything
 * written about one goes to the database. Reads merge the two: the database wins where it
 * has a row, and a seed document that gets reviewed is copied into the database on the
 * way through. That keeps the demo's opening state in version control rather than in a
 * migration, and means an empty database is a working app rather than an empty one.
 */

// ---------------------------------------------------------------- reference data

export function listInvestors() {
  return investors;
}

export function getInvestor(id: string) {
  return investors.find((i) => i.id === id);
}

export function listCompaniesForInvestor(investorId: string) {
  const investor = getInvestor(investorId);
  if (!investor) return [];
  return companies.filter((c) => investor.companyIds.includes(c.id));
}

export function listFundManagers() {
  return fundManagers;
}

export function listCompanies() {
  return companies;
}

export function getCompany(id: string) {
  return companies.find((c) => c.id === id);
}

// ------------------------------------------------------- in-memory fallback

/**
 * Where documents go when no database is configured, so `npm run dev` works on a fresh
 * clone with no environment. Kept on `globalThis` because Next.js bundles each route
 * separately and a module-level object would be a different object per bundle.
 *
 * This is the behaviour that broke in production. It is a local-development convenience
 * now, not the storage strategy, and it says so on startup.
 */
type Memory = {
  documents: Document[];
  statements: Record<string, FinancialStatement>;
  analysis: Record<string, AiAnalysis>;
};

const globalForMemory = globalThis as unknown as {
  __trussMemory?: Memory;
  __trussWarned?: boolean;
};

function memory(): Memory {
  if (!globalForMemory.__trussMemory) {
    globalForMemory.__trussMemory = { documents: [], statements: {}, analysis: {} };
  }
  if (!globalForMemory.__trussWarned) {
    globalForMemory.__trussWarned = true;
    console.warn(
      `[truss] ${misconfiguration()} -- uploads are being kept in memory and will not ` +
        `survive a restart, or be visible to another serverless instance. Fine locally; ` +
        `on a deployment this is the bug that 404s a document after uploading it.`,
    );
  }
  return globalForMemory.__trussMemory;
}

// ------------------------------------------------------------------- mapping

type DocumentRow = {
  id: string;
  company_id: string;
  name: string;
  statement_kind: Document["statementKind"];
  source_format: Document["sourceFormat"];
  uploaded_at: string;
  status: DocumentStatus;
  ai_confidence: number;
  source_file_note: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
};

function toDocument(row: DocumentRow): Document {
  return {
    id: row.id,
    companyId: row.company_id,
    name: row.name,
    statementKind: row.statement_kind,
    sourceFormat: row.source_format,
    uploadedAt: row.uploaded_at,
    status: row.status,
    aiConfidence: row.ai_confidence,
    sourceFileNote: row.source_file_note,
    ...(row.reviewed_by ? { reviewedBy: row.reviewed_by } : {}),
    ...(row.reviewed_at ? { reviewedAt: row.reviewed_at } : {}),
  };
}

function toRow(doc: Document): DocumentRow {
  return {
    id: doc.id,
    company_id: doc.companyId,
    name: doc.name,
    statement_kind: doc.statementKind,
    source_format: doc.sourceFormat,
    uploaded_at: doc.uploadedAt,
    status: doc.status,
    ai_confidence: doc.aiConfidence,
    source_file_note: doc.sourceFileNote,
    reviewed_by: doc.reviewedBy ?? null,
    reviewed_at: doc.reviewedAt ?? null,
  };
}

const newestFirst = (a: Document, b: Document) => (a.uploadedAt < b.uploadedAt ? 1 : -1);

// ------------------------------------------------------------------ documents

export async function listDocumentsForCompany(companyId: string): Promise<Document[]> {
  const client = db();
  const stored = client
    ? ((await client.from("documents").select("*").eq("company_id", companyId)).data ?? [])
        .map((row) => toDocument(row as DocumentRow))
    : memory().documents.filter((d) => d.companyId === companyId);

  // A stored row is the current truth about a document the seed also describes.
  const overridden = new Set(stored.map((d) => d.id));
  const seeds = seedDocuments.filter((d) => d.companyId === companyId && !overridden.has(d.id));
  return [...stored, ...seeds].sort(newestFirst);
}

export async function getDocument(id: string): Promise<Document | undefined> {
  const client = db();
  if (client) {
    const { data } = await client.from("documents").select("*").eq("id", id).maybeSingle();
    if (data) return toDocument(data as DocumentRow);
  } else {
    const held = memory().documents.find((d) => d.id === id);
    if (held) return held;
  }
  return seedDocuments.find((d) => d.id === id);
}

export async function getLatestDocumentOfKind(
  companyId: string,
  kind: Document["statementKind"],
): Promise<Document | undefined> {
  const all = await listDocumentsForCompany(companyId);
  return all.find((d) => d.statementKind === kind);
}

export async function getStatement(
  documentId: string,
): Promise<FinancialStatement | undefined> {
  const client = db();
  if (client) {
    const { data } = await client
      .from("statements")
      .select("*")
      .eq("document_id", documentId)
      .maybeSingle();
    if (data) {
      return {
        kind: data.kind as FinancialStatement["kind"],
        periods: data.periods as string[],
        lines: data.lines as FinancialStatement["lines"],
      };
    }
  } else {
    const held = memory().statements[documentId];
    if (held) return held;
  }
  return statementsByDocumentId[documentId];
}

const NO_ANALYSIS: AiAnalysis = {
  documentAnalysed: true,
  numbersExtracted: true,
  previousPeriodCompared: false,
  issues: [],
  suggestions: [],
};

export async function getAnalysis(documentId: string): Promise<AiAnalysis> {
  const client = db();
  if (client) {
    const { data } = await client
      .from("analyses")
      .select("*")
      .eq("document_id", documentId)
      .maybeSingle();
    if (data) {
      return {
        documentAnalysed: data.document_analysed,
        numbersExtracted: data.numbers_extracted,
        previousPeriodCompared: data.previous_period_compared,
        issues: data.issues as AiAnalysis["issues"],
        suggestions: data.suggestions as string[],
      };
    }
  } else {
    const held = memory().analysis[documentId];
    if (held) return held;
  }
  return analysisByDocumentId[documentId] ?? NO_ANALYSIS;
}

export async function setDocumentStatus(
  id: string,
  status: DocumentStatus,
  reviewedBy?: string,
): Promise<Document | undefined> {
  const doc = await getDocument(id);
  if (!doc) return undefined;

  const updated: Document = {
    ...doc,
    status,
    ...(reviewedBy ? { reviewedBy, reviewedAt: new Date().toISOString() } : {}),
  };

  const client = db();
  if (client) {
    // Upsert rather than update: reviewing a seed document is the first time it exists as
    // a row, and the reviewer's decision is exactly the thing that has to outlive them.
    const { error } = await client.from("documents").upsert(toRow(updated));
    if (error) throw new Error(`could not save the review decision: ${error.message}`);
  } else {
    const held = memory();
    const at = held.documents.findIndex((d) => d.id === id);
    if (at >= 0) held.documents[at] = updated;
    else held.documents.unshift(updated);
  }
  return updated;
}

export async function createUploadedDocument(input: {
  companyId: string;
  name: string;
  sourceFormat: Document["sourceFormat"];
  statementKind: Document["statementKind"];
}): Promise<Document> {
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

  const client = db();
  if (client) {
    const { error } = await client.from("documents").insert(toRow(doc));
    // Failing loudly here is the point. A silent failure is what put a document id in the
    // address bar that nothing could ever resolve.
    if (error) throw new Error(`could not save the uploaded document: ${error.message}`);
  } else {
    memory().documents.unshift(doc);
  }
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
 * Figures are generated, not extracted -- there is no real OCR/LLM backing this yet
 * (docs/truss1.0.md). Real, plausible-looking numbers so the spreadsheet/AI panel have
 * something to show for the demo.
 */
export async function finishProcessing(documentId: string): Promise<Document | undefined> {
  const doc = await getDocument(documentId);
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
  const statement: FinancialStatement = {
    kind: doc.statementKind,
    periods: [current, previous],
    lines,
  };

  const flagged = Math.random() < 0.4;
  const analysis: AiAnalysis = {
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

  const updated: Document = {
    ...doc,
    aiConfidence: 0.9 + Math.random() * 0.09,
    status: flagged ? "needs_review" : "verified",
  };

  const client = db();
  if (client) {
    const { error } = await client.from("documents").upsert(toRow(updated));
    if (error) throw new Error(`could not save the processed document: ${error.message}`);
    await client.from("statements").upsert({
      document_id: documentId,
      kind: statement.kind,
      periods: statement.periods,
      lines: statement.lines,
    });
    await client.from("analyses").upsert({
      document_id: documentId,
      document_analysed: analysis.documentAnalysed,
      numbers_extracted: analysis.numbersExtracted,
      previous_period_compared: analysis.previousPeriodCompared,
      issues: analysis.issues,
      suggestions: analysis.suggestions,
    });
  } else {
    const held = memory();
    const at = held.documents.findIndex((d) => d.id === documentId);
    if (at >= 0) held.documents[at] = updated;
    else held.documents.unshift(updated);
    held.statements[documentId] = statement;
    held.analysis[documentId] = analysis;
  }
  return updated;
}
