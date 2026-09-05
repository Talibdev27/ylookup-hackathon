import { getLatestDocumentOfKind, getStatement } from "@/lib/store";
import { fetchIncomeStatement } from "@/lib/backend";
import { SpreadsheetViewer } from "@/components/SpreadsheetViewer";
import { FinancialTable } from "@/components/FinancialTable";
import { EmptyStatement } from "@/components/EmptyStatement";
import { StatementCaveat } from "@/components/StatementCaveat";
import type { FinancialStatement } from "@/lib/types";

export default async function IncomeStatementPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;

  const real = await fetchIncomeStatement(companyId);
  if (real) {
    const statement: FinancialStatement = {
      kind: "income_statement",
      periods: ["Current"],
      lines: [
        { metric: "Revenues", values: { Current: real.revenues } },
        { metric: "Expenses", values: { Current: real.expenses } },
        { metric: "Net income", values: { Current: real.net_income } },
      ],
    };
    return (
      <div className="space-y-3">
        <StatementCaveat note={real.period} />
        <FinancialTable statement={statement} title={real.legal_entity} />
      </div>
    );
  }

  const doc = getLatestDocumentOfKind(companyId, "income_statement");
  const statement = doc ? getStatement(doc.id) : undefined;

  if (!doc || !statement) return <EmptyStatement label="income statement" companyId={companyId} />;

  return (
    <SpreadsheetViewer document={doc} statement={statement}>
      <FinancialTable statement={statement} />
    </SpreadsheetViewer>
  );
}
