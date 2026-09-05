import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import type { Company } from "@/lib/types";
import { formatDate, formatGbpCompact } from "@/lib/format";

export function CompanyHeader({ company, backHref }: { company: Company; backHref: string }) {
  return (
    <div className="border-b border-line bg-white px-6 py-5 sm:px-8">
      <Link href={backHref} className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </Link>

      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold tracking-tight text-ink">{company.name}</h1>
            <span className="rounded-full bg-navy-50 px-2 py-0.5 text-xs font-medium text-navy-700">
              {company.sector}
            </span>
          </div>
          <p className="mt-1 text-sm text-ink-soft">
            Current Investment:{" "}
            <span className="font-medium text-ink">{formatGbpCompact(company.investmentValueGbp)}</span>
            <span className="mx-2 text-line">·</span>
            Last updated: {formatDate(company.lastUpdated)}
          </p>
        </div>

        <Link
          href={`/company/${company.id}/documents`}
          className="inline-flex items-center gap-1.5 rounded-lg bg-navy-800 px-3.5 py-2 text-sm font-medium text-white hover:bg-navy-700"
        >
          <Plus className="h-4 w-4" /> Upload Document
        </Link>
      </div>
    </div>
  );
}
