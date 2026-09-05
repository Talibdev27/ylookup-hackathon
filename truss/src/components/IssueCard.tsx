"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { AiIssue } from "@/lib/types";

export function IssueCard({ issue }: { issue: AiIssue }) {
  const [open, setOpen] = useState(false);
  const critical = issue.severity === "critical";

  return (
    <div className={`rounded-xl border p-3.5 ${critical ? "border-bad/30 bg-bad-bg/40" : "border-warn/30 bg-warn-bg/40"}`}>
      <p className={`text-sm font-medium ${critical ? "text-bad" : "text-ink"}`}>{issue.title}</p>

      {(issue.current || issue.previous) && (
        <div className="mt-2 flex items-center gap-3 text-xs">
          {issue.previous && (
            <span className="text-ink-soft">
              Previous <span className="font-medium text-ink">{issue.previous}</span>
            </span>
          )}
          {issue.current && (
            <span className="text-ink-soft">
              Current <span className="font-medium text-ink">{issue.current}</span>
            </span>
          )}
          {issue.change && <span className={critical ? "font-medium text-bad" : "font-medium text-warn"}>{issue.change}</span>}
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        className="mt-2 flex items-center gap-1 text-xs font-medium text-navy-700 hover:text-navy-900"
      >
        View Issue
        <ChevronDown className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && <p className="mt-2 text-xs leading-relaxed text-ink-soft">{issue.detail}</p>}
    </div>
  );
}
