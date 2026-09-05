import { getLatestDocumentOfKind, getStatement } from "@/lib/store";
import { SpreadsheetViewer } from "@/components/SpreadsheetViewer";
import { FinancialTable } from "@/components/FinancialTable";
import { EmptyStatement } from "@/components/EmptyStatement";

export default async function IncomeStatementPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  const doc = getLatestDocumentOfKind(companyId, "income_statement");
  const statement = doc ? getStatement(doc.id) : undefined;

  if (!doc || !statement) return <EmptyStatement label="income statement" companyId={companyId} />;

  return (
    <SpreadsheetViewer document={doc} statement={statement}>
      <FinancialTable statement={statement} />
    </SpreadsheetViewer>
  );
}
