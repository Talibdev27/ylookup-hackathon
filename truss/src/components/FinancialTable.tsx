"use client";

import { useMemo, useState } from "react";
import { ArrowUpDown, Search } from "lucide-react";
import type { FinancialStatement } from "@/lib/types";
import { formatGbpCompact, formatPercentChange } from "@/lib/format";
import { SourceTrace } from "./SourceTrace";

const KIND_LABEL: Record<FinancialStatement["kind"], string> = {
  balance_sheet: "Balance Sheet",
  income_statement: "Income Statement",
  cash_flow: "Cash Flow Statement",
};

export function FinancialTable({ statement, title }: { statement: FinancialStatement; title?: string }) {
  const [query, setQuery] = useState("");
  const [sortDesc, setSortDesc] = useState(true);
  const [periodA, periodB] = statement.periods;

  const rows = useMemo(() => {
    let lines = statement.lines.filter((l) => l.metric.toLowerCase().includes(query.toLowerCase()));
    lines = [...lines].sort((a, b) => {
      const av = a.values[periodA] ?? 0;
      const bv = b.values[periodA] ?? 0;
      return sortDesc ? bv - av : av - bv;
    });
    return lines;
  }, [statement.lines, query, sortDesc, periodA]);

  return (
    <div className="rounded-2xl border border-line bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">
            {KIND_LABEL[statement.kind]}
          </p>
          <h3 className="text-base font-semibold text-ink">{title ?? periodA}</h3>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-soft" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search metrics"
            className="w-44 rounded-lg border border-line bg-paper py-1.5 pl-8 pr-3 text-xs outline-none focus:border-navy-500 sm:w-56"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs text-ink-soft">
              <th className="px-5 py-2.5 font-medium">Financial Metric</th>
              <th className="px-3 py-2.5 text-right font-medium">
                <button
                  onClick={() => setSortDesc((v) => !v)}
                  className="inline-flex items-center gap-1 hover:text-ink"
                >
                  {periodA} <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              {periodB && <th className="px-3 py-2.5 text-right font-medium">{periodB}</th>}
              {periodB && <th className="px-5 py-2.5 text-right font-medium">Change</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((line) => {
              const a = line.values[periodA] ?? 0;
              const b = periodB ? line.values[periodB] ?? 0 : undefined;
              return (
                <tr key={line.metric} className="group border-b border-line/70 last:border-0 hover:bg-navy-50/60">
                  <td className="px-5 py-3 font-medium text-ink">
                    <span className="inline-flex items-center gap-1.5">
                      {line.metric}
                      {line.evidence && <SourceTrace evidence={line.evidence} />}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums text-ink">{formatGbpCompact(a)}</td>
                  {periodB && (
                    <td className="px-3 py-3 text-right tabular-nums text-ink-soft">
                      {formatGbpCompact(b ?? 0)}
                    </td>
                  )}
                  {periodB && (
                    <td
                      className={`px-5 py-3 text-right tabular-nums font-medium ${
                        a - (b ?? 0) >= 0 ? "text-good" : "text-bad"
                      }`}
                    >
                      {formatPercentChange(a, b ?? 0)}
                    </td>
                  )}
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-5 py-8 text-center text-sm text-ink-soft">
                  No metrics match “{query}”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
