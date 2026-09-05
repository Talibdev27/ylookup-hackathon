"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { HeaderProfile } from "@/components/HeaderProfile";
import { InvestorList } from "@/components/InvestorList";
import { useSession } from "@/lib/session";
import type { Company, Investor } from "@/lib/types";

export default function FundManagerDashboardPage() {
  const router = useRouter();
  const { session, ready } = useSession();
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [companiesByInvestor, setCompaniesByInvestor] = useState<Record<string, Company[]>>({});

  useEffect(() => {
    if (!ready) return;
    if (!session || session.role !== "fund-manager") {
      router.replace("/");
      return;
    }
    fetch("/api/investors")
      .then((r) => r.json())
      .then(async (d: { investors: Investor[] }) => {
        setInvestors(d.investors ?? []);
        const entries = await Promise.all(
          (d.investors ?? []).map(async (inv) => {
            const res = await fetch(`/api/investors/${inv.id}/companies`);
            const data = await res.json();
            return [inv.id, data.companies ?? []] as const;
          })
        );
        setCompaniesByInvestor(Object.fromEntries(entries));
      });
  }, [ready, session, router]);

  if (!ready || !session) return null;

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader subtitle="Manage investors and review their financial data." right={<HeaderProfile />} />

      <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6">
        <h2 className="mb-3 text-sm font-semibold text-ink">My Investors</h2>
        <InvestorList investors={investors} companiesByInvestor={companiesByInvestor} />
      </div>
    </div>
  );
}
