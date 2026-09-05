import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { Company } from "@/lib/types";
import { formatDate, formatGbpCompact } from "@/lib/format";

export function InvestmentList({ companies }: { companies: Company[] }) {
  if (companies.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-line px-4 py-6 text-center text-sm text-ink-soft">
        No investments yet. Documents you upload will appear here once a company is linked.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-white">
      {companies.map((company, i) => (
        <li key={company.id}>
          <Link
            href={`/company/${company.id}`}
            className="flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-navy-50"
          >
            <span className="w-6 shrink-0 font-mono text-xs text-ink-soft">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="flex-1 min-w-0">
              <span className="block truncate font-medium text-ink">{company.name}</span>
              <span className="block text-xs text-ink-soft">{company.sector}</span>
            </span>
            <span className="hidden text-right sm:block">
              <span className="block text-sm font-medium text-ink">
                {formatGbpCompact(company.investmentValueGbp)}
              </span>
              <span className="block text-xs text-ink-soft">Updated {formatDate(company.lastUpdated)}</span>
            </span>
            <span
              className={`hidden rounded-full px-2 py-0.5 text-xs font-medium sm:inline-block ${
                company.status === "active" ? "bg-good-bg text-good" : "bg-paper text-ink-soft"
              }`}
            >
              {company.status === "active" ? "Active" : "Inactive"}
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-ink-soft" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
