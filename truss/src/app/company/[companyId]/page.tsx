import { getStatement, listDocumentsForCompany } from "@/lib/store";
import { SpreadsheetViewer } from "@/components/SpreadsheetViewer";
import { FinancialTable } from "@/components/FinancialTable";
import { EmptyStatement } from "@/components/EmptyStatement";

export default async function CompanyOverviewPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  const doc = (await listDocumentsForCompany(companyId))[0];
  const statement = doc ? await getStatement(doc.id) : undefined;

  if (!doc || !statement) return <EmptyStatement label="spreadsheet" companyId={companyId} />;

  return (
    <SpreadsheetViewer document={doc} statement={statement}>
      <FinancialTable statement={statement} />
    </SpreadsheetViewer>
  );
}
