"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import type { Evidence } from "@/lib/types";
import { formatConfidence } from "@/lib/format";

export function SourceTrace({ evidence }: { evidence: Evidence }) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        title="View source"
        className="rounded p-0.5 text-ink-soft/60 opacity-0 transition-opacity hover:text-navy-700 group-hover:opacity-100"
      >
        <FileText className="h-3 w-3" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-1 w-56 rounded-lg border border-line bg-white p-3 text-left text-xs shadow-card">
            <p className="font-medium text-ink">AI confidence {formatConfidence(evidence.confidence)}</p>
            <p className="mt-1 text-ink-soft">
              Source: {evidence.documentName}
              <br />
              Page {evidence.page}
            </p>
          </div>
        </>
      )}
    </span>
  );
}
