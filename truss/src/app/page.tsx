"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Building2, UserRound } from "lucide-react";
import { useSession } from "@/lib/session";
import type { FundManager, Investor } from "@/lib/types";

// No real auth in v1 (docs/truss1.0.md) — one click drops you into the first
// investor/fund manager on file rather than picking a specific one.
export default function RolePickerPage() {
  const router = useRouter();
  const { setSession } = useSession();
  const [investor, setInvestor] = useState<Investor | null>(null);
  const [fundManager, setFundManager] = useState<FundManager | null>(null);

  useEffect(() => {
    fetch("/api/investors")
      .then((r) => r.json())
      .then((d) => setInvestor((d.investors ?? [])[0] ?? null));
    fetch("/api/fund-managers")
      .then((r) => r.json())
      .then((d) => setFundManager((d.fundManagers ?? [])[0] ?? null));
  }, []);

  function enterAsInvestor() {
    if (!investor) return;
    setSession({ role: "investor", actorId: investor.id, actorName: investor.name });
    router.push("/investor");
  }

  function enterAsFundManager() {
    if (!fundManager) return;
    setSession({ role: "fund-manager", actorId: fundManager.id, actorName: fundManager.name });
    router.push("/fund-manager");
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-paper px-4 py-16">
      <div className="mb-10 flex flex-col items-center gap-3 text-center">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-navy-800">
          <span className="h-3 w-3 rounded-[2px] bg-white" />
        </span>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">TRUSS</h1>
        <p className="text-sm text-ink-soft">Financial data, structured.</p>
      </div>

      <div className="grid w-full max-w-xl grid-cols-1 gap-4 sm:grid-cols-2">
        <button
          onClick={enterAsInvestor}
          disabled={!investor}
          className="group flex flex-col items-start gap-4 rounded-2xl bg-navy-800 p-6 text-left text-white transition-colors hover:bg-navy-700 disabled:opacity-60"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
            <UserRound className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-base font-semibold">Continue as Investor</span>
            <span className="mt-0.5 block text-sm text-white/70">
              Your investments and their financial data
            </span>
          </span>
          <ArrowRight className="h-4 w-4 text-white/70 transition-transform group-hover:translate-x-0.5" />
        </button>

        <button
          onClick={enterAsFundManager}
          disabled={!fundManager}
          className="group flex flex-col items-start gap-4 rounded-2xl bg-navy-800 p-6 text-left text-white transition-colors hover:bg-navy-700 disabled:opacity-60"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
            <Building2 className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-base font-semibold">Continue as Fund Manager</span>
            <span className="mt-0.5 block text-sm text-white/70">
              Your investors and their companies
            </span>
          </span>
          <ArrowRight className="h-4 w-4 text-white/70 transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </div>
  );
}
