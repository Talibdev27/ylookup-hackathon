"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { HeaderProfile } from "@/components/HeaderProfile";
import { UploadDropzone } from "@/components/UploadDropzone";
import { InvestmentList } from "@/components/InvestmentList";
import { useSession } from "@/lib/session";
import type { Company } from "@/lib/types";

export default function InvestorDashboardPage() {
  const router = useRouter();
  const { session, ready } = useSession();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [targetCompanyId, setTargetCompanyId] = useState<string>("");

  useEffect(() => {
    if (!ready) return;
    if (!session || session.role !== "investor") {
      router.replace("/");
      return;
    }
    fetch(`/api/investors/${session.actorId}/companies`)
      .then((r) => r.json())
      .then((d: { companies: Company[] }) => {
        setCompanies(d.companies ?? []);
        setTargetCompanyId((d.companies ?? [])[0]?.id ?? "");
      });
  }, [ready, session, router]);

  if (!ready || !session) return null;

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader subtitle="Financial data, structured." right={<HeaderProfile />} />

      <div className="mx-auto w-full max-w-3xl flex-1 space-y-8 px-4 py-8 sm:px-6">
        <section>
          {companies.length > 1 && (
            <div className="mb-3 flex items-center justify-end gap-2 text-xs text-ink-soft">
              Uploading for
              <select
                value={targetCompanyId}
                onChange={(e) => setTargetCompanyId(e.target.value)}
                className="rounded-md border border-line bg-white px-2 py-1 text-xs text-ink"
              >
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          {targetCompanyId && (
            <UploadDropzone
              companyId={targetCompanyId}
              onUploaded={({ document }) => router.push(`/document/${document.id}`)}
            />
          )}
        </section>

        <section>
          <h2 className="mb-3 text-sm font-semibold text-ink">Your Investments</h2>
          <InvestmentList companies={companies} />
        </section>
      </div>
    </div>
  );
}
