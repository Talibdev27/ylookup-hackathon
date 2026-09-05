import { getLatestDocumentOfKind, getStatement } from "@/lib/store";
import { fetchCashFlow, fetchBalanceSheet } from "@/lib/backend";
import { SpreadsheetViewer } from "@/components/SpreadsheetViewer";
import { FinancialTable } from "@/components/FinancialTable";
import { EmptyStatement } from "@/components/EmptyStatement";
import { CircleSlash } from "lucide-react";

export default async function CashFlowPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;

  // A real company (one of the four funds) has no cash-flow endpoint that returns
  // fabricated numbers -- see src/ui/app.py's api_cash_flow. Check whether this is one
  // of them via the balance-sheet endpoint (cheap, and every real company has one),
  // then show the honest reason rather than the generic "upload a document" empty state,
  // which would wrongly imply that uploading something fixes this.
  const isRealCompany = await fetchBalanceSheet(companyId);
  if (isRealCompany) {
    const cashFlow = await fetchCashFlow(companyId);
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-line bg-white px-6 py-16 text-center">
        <CircleSlash className="h-8 w-8 text-line" />
        <p className="text-sm font-medium text-ink">Not available for {isRealCompany.legal_entity}</p>
        <p className="max-w-md text-xs text-ink-soft">
          {cashFlow?.reason ??
            "This data has no operating/investing/financing classification to build a cash flow statement from."}
        </p>
      </div>
    );
  }

  const doc = getLatestDocumentOfKind(companyId, "cash_flow");
  const statement = doc ? getStatement(doc.id) : undefined;

  if (!doc || !statement) return <EmptyStatement label="cash flow statement" companyId={companyId} />;

  return (
    <SpreadsheetViewer document={doc} statement={statement}>
      <FinancialTable statement={statement} />
    </SpreadsheetViewer>
  );
}
