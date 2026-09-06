import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { CompanyHeader } from "@/components/CompanyHeader";
import { DocumentTabs } from "@/components/DocumentTabs";
import { RecentUploads } from "@/components/RecentUploads";
import { AIAgentPanel } from "@/components/AIAgentPanel";
import { HeaderProfile } from "@/components/HeaderProfile";
import { getAnalysis, getCompany, listDocumentsForCompany } from "@/lib/store";

export default async function CompanyLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  const company = getCompany(companyId);
  if (!company) notFound();

  const documents = await listDocumentsForCompany(companyId);
  const featured = documents.find((d) => d.status === "needs_review" || d.status === "critical") ?? documents[0];
  const analysis = featured
    ? await getAnalysis(featured.id)
    : { documentAnalysed: false, numbersExtracted: false, previousPeriodCompared: false, issues: [], suggestions: [] };

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader href="/" right={<HeaderProfile />} />
      <CompanyHeader company={company} backHref="/" />
      <DocumentTabs companyId={company.id} />

      <div className="grid flex-1 grid-cols-1 gap-4 bg-paper p-4 sm:p-6 lg:grid-cols-[240px_minmax(0,1fr)_300px] lg:gap-5 lg:p-6">
        <aside className="order-2 lg:order-1">
          <RecentUploads companyId={company.id} documents={documents} activeDocumentId={featured?.id} />
        </aside>

        <main className="order-1 min-w-0 lg:order-2">{children}</main>

        <aside className="order-3">
          <AIAgentPanel analysis={analysis} />
        </aside>
      </div>
    </div>
  );
}
