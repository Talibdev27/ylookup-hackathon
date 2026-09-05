"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { Company, Investor } from "@/lib/types";
import { formatGbpCompact } from "@/lib/format";

export function InvestorList({
  investors,
  companiesByInvestor,
}: {
  investors: Investor[];
  companiesByInvestor: Record<string, Company[]>;
}) {
  return (
    <ul className="space-y-2">
      {investors.map((investor, i) => (
        <InvestorRow
          key={investor.id}
          index={i}
          investor={investor}
          companies={companiesByInvestor[investor.id] ?? []}
        />
      ))}
    </ul>
  );
}

function InvestorRow({
  index,
  investor,
  companies,
}: {
  index: number;
  investor: Investor;
  companies: Company[];
}) {
  const [open, setOpen] = useState(index === 0);

  return (
    <li className="overflow-hidden rounded-xl border border-line bg-white">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-4 px-4 py-3.5 text-left transition-colors hover:bg-navy-50"
      >
        <span className="w-6 shrink-0 font-mono text-xs text-ink-soft">
          {String(index + 1).padStart(2, "0")}
        </span>
        <span className="flex-1 min-w-0">
          <span className="block font-medium text-ink">{investor.name}</span>
          <span className="block text-xs text-ink-soft">
            {companies.length} {companies.length === 1 ? "company" : "companies"}
          </span>
        </span>
        <ChevronRight className={`h-4 w-4 text-ink-soft transition-transform ${open ? "rotate-90" : ""}`} />
      </button>

      {open && (
        <ul className="border-t border-line bg-paper/60 pb-2 pl-11 pr-3 pt-2">
          {companies.map((company, i) => {
            const isLast = i === companies.length - 1;
            return (
              <li key={company.id} className="relative">
                <span
                  aria-hidden
                  className={`absolute left-[-16px] top-0 w-3 border-l border-line ${
                    isLast ? "h-4" : "h-full"
                  }`}
                />
                <span aria-hidden className="absolute left-[-16px] top-4 w-3 border-t border-line" />
                <CompanyRow company={company} />
              </li>
            );
          })}
        </ul>
      )}
    </li>
  );
}

function CompanyRow({ company }: { company: Company }) {
  return (
    <Link
      href={`/company/${company.id}`}
      className="flex items-center justify-between gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors hover:bg-white"
    >
      <span className="text-ink">{company.name}</span>
      <span className="text-xs text-ink-soft">{formatGbpCompact(company.investmentValueGbp)}</span>
    </Link>
  );
}
