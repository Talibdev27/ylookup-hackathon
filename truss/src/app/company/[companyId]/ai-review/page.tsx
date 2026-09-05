import { getAnalysis, listDocumentsForCompany } from "@/lib/store";
import { IssueCard } from "@/components/IssueCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CheckCircle2 } from "lucide-react";

export default async function AiReviewPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  const documents = listDocumentsForCompany(companyId);
  const withIssues = documents
    .map((doc) => ({ doc, analysis: getAnalysis(doc.id) }))
    .filter((d) => d.analysis.issues.length > 0);

  if (withIssues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-line bg-white px-6 py-16 text-center">
        <CheckCircle2 className="h-8 w-8 text-good" />
        <p className="text-sm font-medium text-ink">Nothing needs attention</p>
        <p className="max-w-xs text-xs text-ink-soft">
          The AI Agent has not flagged any discrepancies across this company&apos;s documents.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {withIssues.map(({ doc, analysis }) => (
        <div key={doc.id} className="rounded-2xl border border-line bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-medium text-ink">{doc.name}</p>
            <StatusBadge status={doc.status} />
          </div>
          <div className="space-y-2.5">
            {analysis.issues.map((issue) => (
              <IssueCard key={issue.id} issue={issue} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
