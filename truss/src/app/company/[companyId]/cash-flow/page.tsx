import { getLatestDocumentOfKind, getStatement } from "@/lib/store";
import { SpreadsheetViewer } from "@/components/SpreadsheetViewer";
import { FinancialTable } from "@/components/FinancialTable";
import { EmptyStatement } from "@/components/EmptyStatement";

export default async function CashFlowPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  const doc = getLatestDocumentOfKind(companyId, "cash_flow");
  const statement = doc ? getStatement(doc.id) : undefined;

  if (!doc || !statement) return <EmptyStatement label="cash flow statement" companyId={companyId} />;

  return (
    <SpreadsheetViewer document={doc} statement={statement}>
      <FinancialTable statement={statement} />
    </SpreadsheetViewer>
  );
}
