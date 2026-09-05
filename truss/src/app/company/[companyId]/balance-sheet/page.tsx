import { getLatestDocumentOfKind, getStatement } from "@/lib/store";
import { fetchBalanceSheet } from "@/lib/backend";
import { SpreadsheetViewer } from "@/components/SpreadsheetViewer";
import { FinancialTable } from "@/components/FinancialTable";
import { EmptyStatement } from "@/components/EmptyStatement";
import { StatementCaveat } from "@/components/StatementCaveat";
import type { FinancialStatement } from "@/lib/types";

export default async function BalanceSheetPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;

  // Real companies (the Python matcher's own four funds) are served from the real
  // backend; everything else keeps using the mock document/upload store. See
  // docs/backend-integration.md for why these are two different data paths.
  const real = await fetchBalanceSheet(companyId);
  if (real) {
    const statement: FinancialStatement = {
      kind: "balance_sheet",
      periods: ["Current"],
      lines: [
        { metric: "Assets", values: { Current: real.assets } },
        { metric: "Liabilities", values: { Current: real.liabilities } },
        { metric: "Capital", values: { Current: real.capital } },
      ],
    };
    return (
      <div className="space-y-3">
        <StatementCaveat ties={real.ties} note={real.period} />
        <FinancialTable statement={statement} title={real.legal_entity} />
      </div>
    );
  }

  const doc = getLatestDocumentOfKind(companyId, "balance_sheet");
  const statement = doc ? getStatement(doc.id) : undefined;

  if (!doc || !statement) return <EmptyStatement label="balance sheet" companyId={companyId} />;

  return (
    <SpreadsheetViewer document={doc} statement={statement}>
      <FinancialTable statement={statement} />
    </SpreadsheetViewer>
  );
}
