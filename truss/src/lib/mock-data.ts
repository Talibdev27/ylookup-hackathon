import type {
  AiAnalysis,
  Company,
  Document,
  FinancialStatement,
  FundManager,
  Investor,
} from "./types";

// Seed data for the TRUSS demo. Mirrors the examples in docs/TRUSS.md (§8, §12, §14,
// §16.1, §22, §29) rather than inventing a different story.

export const investors: Investor[] = [
  {
    id: "inv-a",
    name: "Investor A",
    organisationId: "ORG-4471",
    contactEmail: "contact@investor-a.example",
    companyIds: ["co-a", "co-b", "co-c"],
  },
  {
    id: "inv-b",
    name: "Investor B",
    organisationId: "ORG-4488",
    contactEmail: "contact@investor-b.example",
    companyIds: ["co-d", "co-e"],
  },
  {
    id: "inv-c",
    name: "Investor C",
    organisationId: "ORG-4502",
    contactEmail: "contact@investor-c.example",
    companyIds: ["co-f"],
  },
];

export const fundManagers: FundManager[] = [
  {
    id: "fm-1",
    name: "Fund Manager",
    contactEmail: "manager@truss.example",
    investorIds: ["inv-a", "inv-b", "inv-c"],
  },
];

export const companies: Company[] = [
  { id: "co-a", name: "Company A", sector: "Technology", investmentValueGbp: 540000, status: "active", lastUpdated: "2026-09-05" },
  { id: "co-b", name: "Company B", sector: "Healthcare", investmentValueGbp: 310000, status: "active", lastUpdated: "2026-08-22" },
  { id: "co-c", name: "Company C", sector: "Consumer", investmentValueGbp: 175000, status: "active", lastUpdated: "2026-07-30" },
  { id: "co-d", name: "Company D", sector: "Industrials", investmentValueGbp: 420000, status: "active", lastUpdated: "2026-08-15" },
  { id: "co-e", name: "Company E", sector: "Technology", investmentValueGbp: 260000, status: "inactive", lastUpdated: "2026-05-02" },
  { id: "co-f", name: "Company F", sector: "Energy", investmentValueGbp: 690000, status: "active", lastUpdated: "2026-09-01" },
];

export const documents: Document[] = [
  { id: "doc-a-1", companyId: "co-a", name: "Q2 2026 Statement", statementKind: "balance_sheet", sourceFormat: "pdf", uploadedAt: "2026-09-02", status: "needs_review", aiConfidence: 0.98, sourceFileNote: "Q2_Statement.pdf, page 4" },
  { id: "doc-a-2", companyId: "co-a", name: "Q1 2026 Statement", statementKind: "balance_sheet", sourceFormat: "pdf", uploadedAt: "2026-08-04", status: "verified", aiConfidence: 0.99, sourceFileNote: "Q1_Statement.pdf, page 3", reviewedBy: "Investor A", reviewedAt: "2026-08-05" },
  { id: "doc-a-3", companyId: "co-a", name: "Annual Statement", statementKind: "income_statement", sourceFormat: "screenshot", uploadedAt: "2026-07-12", status: "needs_review", aiConfidence: 0.87, sourceFileNote: "Annual_Statement.png, page 1" },
  { id: "doc-a-4", companyId: "co-a", name: "Q4 2025 Statement", statementKind: "cash_flow", sourceFormat: "pdf", uploadedAt: "2026-04-08", status: "verified", aiConfidence: 0.97, sourceFileNote: "Q4_2025_Statement.pdf, page 6", reviewedBy: "Investor A", reviewedAt: "2026-04-09" },

  { id: "doc-b-1", companyId: "co-b", name: "Q2 2026 Statement", statementKind: "balance_sheet", sourceFormat: "jpg", uploadedAt: "2026-08-30", status: "verified", aiConfidence: 0.95, sourceFileNote: "Q2_Statement.jpg, page 1", reviewedBy: "Investor A", reviewedAt: "2026-08-31" },
  { id: "doc-b-2", companyId: "co-b", name: "Q1 2026 Statement", statementKind: "balance_sheet", sourceFormat: "pdf", uploadedAt: "2026-05-30", status: "verified", aiConfidence: 0.96, sourceFileNote: "Q1_Statement.pdf, page 2", reviewedBy: "Investor A", reviewedAt: "2026-05-31" },

  { id: "doc-d-1", companyId: "co-d", name: "Q2 2026 Statement", statementKind: "income_statement", sourceFormat: "excel", uploadedAt: "2026-08-20", status: "processing", aiConfidence: 0, sourceFileNote: "Q2_Statement.xlsx" },
];

const balanceSheetA: FinancialStatement = {
  kind: "balance_sheet",
  periods: ["Q2 2026", "Q1 2026"],
  lines: [
    { metric: "Cash", values: { "Q2 2026": 482000, "Q1 2026": 431000 }, evidence: { documentName: "Q2_Statement.pdf", page: 4, confidence: 0.98 } },
    { metric: "Receivables", values: { "Q2 2026": 210000, "Q1 2026": 188000 }, evidence: { documentName: "Q2_Statement.pdf", page: 4, confidence: 0.97 } },
    { metric: "Total Assets", values: { "Q2 2026": 2800000, "Q1 2026": 2500000 }, evidence: { documentName: "Q2_Statement.pdf", page: 4, confidence: 0.98 } },
    { metric: "Liabilities", values: { "Q2 2026": 1100000, "Q1 2026": 980000 }, evidence: { documentName: "Q2_Statement.pdf", page: 5, confidence: 0.96 } },
    { metric: "Equity", values: { "Q2 2026": 1700000, "Q1 2026": 1500000 }, evidence: { documentName: "Q2_Statement.pdf", page: 5, confidence: 0.98 } },
  ],
};

const incomeStatementA: FinancialStatement = {
  kind: "income_statement",
  periods: ["Q2 2026", "Q1 2026"],
  lines: [
    { metric: "Revenue", values: { "Q2 2026": 1240000, "Q1 2026": 1180000 }, evidence: { documentName: "Annual_Statement.png", page: 1, confidence: 0.87 } },
    { metric: "Operating Expenses", values: { "Q2 2026": 860000, "Q1 2026": 790000 }, evidence: { documentName: "Annual_Statement.png", page: 1, confidence: 0.85 } },
    { metric: "Net Income", values: { "Q2 2026": 380000, "Q1 2026": 390000 }, evidence: { documentName: "Annual_Statement.png", page: 1, confidence: 0.86 } },
  ],
};

const cashFlowA: FinancialStatement = {
  kind: "cash_flow",
  periods: ["Q4 2025", "Q3 2025"],
  lines: [
    { metric: "Opening Cash", values: { "Q4 2025": 402000, "Q3 2025": 365000 } },
    { metric: "Net Cash from Operations", values: { "Q4 2025": 210000, "Q3 2025": 240000 } },
    { metric: "Net Cash used in Investing", values: { "Q4 2025": -95000, "Q3 2025": -80000 } },
    { metric: "Net Cash from Financing", values: { "Q4 2025": -35000, "Q3 2025": -20000 } },
    { metric: "Closing Cash", values: { "Q4 2025": 482000, "Q3 2025": 402000 } },
  ],
};

const balanceSheetB: FinancialStatement = {
  kind: "balance_sheet",
  periods: ["Q2 2026", "Q1 2026"],
  lines: [
    { metric: "Cash", values: { "Q2 2026": 156000, "Q1 2026": 149000 } },
    { metric: "Receivables", values: { "Q2 2026": 88000, "Q1 2026": 81000 } },
    { metric: "Total Assets", values: { "Q2 2026": 940000, "Q1 2026": 905000 } },
    { metric: "Liabilities", values: { "Q2 2026": 310000, "Q1 2026": 300000 } },
    { metric: "Equity", values: { "Q2 2026": 630000, "Q1 2026": 605000 } },
  ],
};

export const statementsByDocumentId: Record<string, FinancialStatement> = {
  "doc-a-1": balanceSheetA,
  "doc-a-3": incomeStatementA,
  "doc-a-4": cashFlowA,
  "doc-b-1": balanceSheetB,
  "doc-b-2": balanceSheetB,
};

export const analysisByDocumentId: Record<string, AiAnalysis> = {
  "doc-a-1": {
    documentAnalysed: true,
    numbersExtracted: true,
    previousPeriodCompared: true,
    issues: [
      {
        id: "issue-a-1-revenue",
        title: "Revenue discrepancy",
        detail:
          "Revenue increased by 5.1% compared with the previous statement. Review supporting documentation.",
        metric: "Revenue",
        current: "£1.24M",
        previous: "£1.18M",
        change: "+5.1%",
        severity: "warn",
      },
      {
        id: "issue-a-1-cash",
        title: "Cash movement",
        detail: "Cash decreased by 18% despite increased revenue.",
        severity: "warn",
      },
    ],
    suggestions: [
      "Review unusual revenue movement",
      "Confirm cash-flow classification",
      "Compare against previous quarter",
    ],
  },
  "doc-a-3": {
    documentAnalysed: true,
    numbersExtracted: true,
    previousPeriodCompared: true,
    issues: [],
    suggestions: ["Confirm operating expense classification against Q1"],
  },
};
