import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { notFound } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { HeaderProfile } from "@/components/HeaderProfile";
import { SpreadsheetViewer } from "@/components/SpreadsheetViewer";
import { FinancialTable } from "@/components/FinancialTable";
import { AIAgentPanel } from "@/components/AIAgentPanel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { getAnalysis, getCompany, getDocument, getStatement } from "@/lib/store";

export default async function DocumentPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const doc = await getDocument(documentId);
  if (!doc) notFound();

  const company = getCompany(doc.companyId);
  const statement = await getStatement(documentId);
  const analysis = await getAnalysis(documentId);

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader right={<HeaderProfile />} />

      <div className="border-b border-line bg-white px-6 py-5 sm:px-8">
        <Link
          href={company ? `/company/${company.id}/documents` : "/"}
          className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to {company?.name ?? "company"}
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight text-ink">{doc.name}</h1>
          <StatusBadge status={doc.status} />
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-5 bg-paper p-4 sm:p-6 lg:grid-cols-[minmax(0,1fr)_300px] lg:p-6">
        <main className="min-w-0">
          {statement ? (
            <SpreadsheetViewer document={doc} statement={statement}>
              <FinancialTable statement={statement} />
            </SpreadsheetViewer>
          ) : (
            <div className="rounded-2xl border border-dashed border-line bg-white px-6 py-16 text-center text-sm text-ink-soft">
              Still processing — check back shortly.
            </div>
          )}
        </main>
        <aside>
          <AIAgentPanel analysis={analysis} />
        </aside>
      </div>
    </div>
  );
}
