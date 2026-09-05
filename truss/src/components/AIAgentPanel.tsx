import type { AiAnalysis } from "@/lib/types";
import { AIInsight } from "./AIInsight";
import { IssueCard } from "./IssueCard";

export function AIAgentPanel({ analysis }: { analysis: AiAnalysis }) {
  const issueCount = analysis.issues.length;

  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">AI Agent</h2>
        <span className="flex items-center gap-1.5 text-xs text-good">
          <span className="h-1.5 w-1.5 rounded-full bg-good" /> Monitoring
        </span>
      </div>

      <h3 className="mt-4 text-xs font-medium uppercase tracking-wide text-ink-soft">Analysis</h3>
      <ul className="mt-2 space-y-1.5">
        <AIInsight label="Document analysed" done={analysis.documentAnalysed} />
        <AIInsight label="Numbers extracted" done={analysis.numbersExtracted} />
        <AIInsight label="Previous period compared" done={analysis.previousPeriodCompared} />
        {issueCount > 0 && (
          <AIInsight label={`${issueCount} ${issueCount === 1 ? "issue" : "issues"} found`} warn />
        )}
      </ul>

      {issueCount > 0 && (
        <div className="mt-4 space-y-2.5">
          {analysis.issues.map((issue) => (
            <IssueCard key={issue.id} issue={issue} />
          ))}
        </div>
      )}

      {analysis.suggestions.length > 0 && (
        <div className="mt-5 border-t border-line pt-4">
          <h3 className="text-xs font-medium uppercase tracking-wide text-ink-soft">Suggestions</h3>
          <ul className="mt-2 space-y-1.5">
            {analysis.suggestions.map((s) => (
              <li key={s} className="flex gap-2 text-xs text-ink-soft">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-navy-400" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
