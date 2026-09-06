"use client";

import { useState } from "react";
import type { Document, FinancialStatement } from "@/lib/types";
import { formatConfidence, formatDate } from "@/lib/format";
import { StatusBadge } from "./ui/StatusBadge";
import { ExportButton } from "./ui/ExportButton";
import { ReviewButton } from "./ReviewButton";
import { ViewSourceButton } from "./ViewSourceButton";

export function SpreadsheetViewer({
  document: doc,
  statement,
  children,
}: {
  document: Document;
  statement: FinancialStatement;
  /** The FinancialTable (or similar), rendered below the metadata bar. */
  children: React.ReactNode;
}) {
  const [current, setCurrent] = useState(doc);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-white px-5 py-4">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-ink-soft">
          <span className="text-sm font-medium text-ink">{current.name}</span>
          <StatusBadge status={current.status} />
          <span>Uploaded {formatDate(current.uploadedAt)}</span>
          {current.aiConfidence === null ? (
            <span>Not analysed</span>
          ) : (
            <span>AI confidence {formatConfidence(current.aiConfidence)}</span>
          )}
          {current.reviewedBy && (
            <span>
              Reviewed by {current.reviewedBy} · {current.reviewedAt ? formatDate(current.reviewedAt) : ""}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ExportButton documentId={current.id} />
          <ViewSourceButton sourceFileNote={current.sourceFileNote} />
          <ReviewButton documentId={current.id} action="flag" onDone={setCurrent} />
          <ReviewButton documentId={current.id} action="approve" onDone={setCurrent} />
        </div>
      </div>

      {children}
    </div>
  );
}
