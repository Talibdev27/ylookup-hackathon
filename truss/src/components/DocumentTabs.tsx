"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileSpreadsheet, Scale, Wallet, TrendingUp, FolderOpen, Sparkles } from "lucide-react";

export function DocumentTabs({ companyId }: { companyId: string }) {
  const pathname = usePathname();
  const base = `/company/${companyId}`;

  const tabs = [
    { label: "Excel Spreadsheet", href: base, icon: FileSpreadsheet },
    { label: "Balance Sheet", href: `${base}/balance-sheet`, icon: Scale },
    { label: "Cash Flow", href: `${base}/cash-flow`, icon: Wallet },
    { label: "Income Statement", href: `${base}/income-statement`, icon: TrendingUp },
    { label: "Documents", href: `${base}/documents`, icon: FolderOpen },
    { label: "AI Review", href: `${base}/ai-review`, icon: Sparkles },
  ];

  return (
    <nav className="scrollbar-thin flex gap-1 overflow-x-auto border-b border-line bg-white px-4 sm:px-8">
      {tabs.map((tab) => {
        const active = pathname === tab.href;
        const Icon = tab.icon;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
              active
                ? "border-navy-800 text-navy-800"
                : "border-transparent text-ink-soft hover:text-ink"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
