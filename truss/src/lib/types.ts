// Domain types for TRUSS. See docs/TRUSS.md for the product spec these encode.

export type Role = "investor" | "fund-manager";

export type DocumentStatus = "verified" | "needs_review" | "processing" | "uploaded" | "critical";

export type SourceFormat = "pdf" | "jpg" | "png" | "screenshot" | "excel" | "csv";

export type StatementKind = "balance_sheet" | "income_statement" | "cash_flow";

export interface Investor {
  id: string;
  name: string;
  organisationId: string;
  contactEmail: string;
  companyIds: string[];
}

export interface FundManager {
  id: string;
  name: string;
  contactEmail: string;
  investorIds: string[];
}

export interface Company {
  id: string;
  name: string;
  sector: string;
  investmentValueGbp: number;
  status: "active" | "inactive";
  lastUpdated: string; // ISO date
}

export interface Evidence {
  documentName: string;
  page: number;
  confidence: number; // 0-1
}

export interface FinancialLine {
  metric: string;
  values: Record<string, number>; // period label -> value in GBP
  evidence?: Evidence;
}

export interface FinancialStatement {
  kind: StatementKind;
  periods: string[]; // ordered, most recent first
  lines: FinancialLine[];
}

export interface AiIssue {
  id: string;
  title: string;
  detail: string;
  metric?: string;
  current?: string;
  previous?: string;
  change?: string;
  severity: "warn" | "critical";
}

export interface AiAnalysis {
  documentAnalysed: boolean;
  numbersExtracted: boolean;
  previousPeriodCompared: boolean;
  issues: AiIssue[];
  suggestions: string[];
}

export interface Document {
  id: string;
  companyId: string;
  name: string;
  statementKind: StatementKind;
  sourceFormat: SourceFormat;
  uploadedAt: string; // ISO date
  status: DocumentStatus;
  aiConfidence: number; // 0-1
  sourceFileNote: string;
  reviewedBy?: string;
  reviewedAt?: string;
}
