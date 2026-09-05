"use client";

import { useState } from "react";
import { ChevronDown, LogOut, Settings, User } from "lucide-react";
import { useSession } from "@/lib/session";
import { formatGbpCompact } from "@/lib/format";

export function ProfileMenu({
  organisationId,
  contactEmail,
  totalInvestmentGbp,
  investmentCount,
}: {
  organisationId?: string;
  contactEmail?: string;
  totalInvestmentGbp?: number;
  investmentCount?: number;
}) {
  const { session, clearSession } = useSession();
  const [open, setOpen] = useState(false);

  if (!session) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full border border-line bg-white py-1 pl-1 pr-3 text-sm hover:border-navy-500"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-navy-800 text-white">
          <User className="h-3.5 w-3.5" />
        </span>
        <span className="font-medium text-ink">{session.actorName}</span>
        <ChevronDown className="h-3.5 w-3.5 text-ink-soft" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-2 w-72 rounded-xl border border-line bg-white p-4 shadow-card">
            <p className="text-sm font-semibold text-ink">{session.actorName}</p>
            <p className="mt-0.5 text-xs text-ink-soft capitalize">{session.role.replace("-", " ")}</p>

            <dl className="mt-4 space-y-2 border-t border-line pt-3 text-xs">
              {organisationId && (
                <div className="flex justify-between">
                  <dt className="text-ink-soft">Organisation ID</dt>
                  <dd className="font-medium text-ink">{organisationId}</dd>
                </div>
              )}
              {contactEmail && (
                <div className="flex justify-between">
                  <dt className="text-ink-soft">Contact</dt>
                  <dd className="font-medium text-ink">{contactEmail}</dd>
                </div>
              )}
              {typeof totalInvestmentGbp === "number" && (
                <div className="flex justify-between">
                  <dt className="text-ink-soft">Total investment value</dt>
                  <dd className="font-medium text-ink">{formatGbpCompact(totalInvestmentGbp)}</dd>
                </div>
              )}
              {typeof investmentCount === "number" && (
                <div className="flex justify-between">
                  <dt className="text-ink-soft">Number of investments</dt>
                  <dd className="font-medium text-ink">{investmentCount}</dd>
                </div>
              )}
            </dl>

            <div className="mt-3 flex flex-col border-t border-line pt-3">
              <button className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-ink-soft hover:bg-navy-50 hover:text-ink">
                <Settings className="h-4 w-4" /> Settings
              </button>
              <button
                onClick={clearSession}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-ink-soft hover:bg-navy-50 hover:text-ink"
              >
                <LogOut className="h-4 w-4" /> Switch role
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
