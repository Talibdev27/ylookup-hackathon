"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "@/lib/session";
import { ProfileMenu } from "./ProfileMenu";
import type { Company, Investor } from "@/lib/types";

/** Reads the current session and fetches the bits ProfileMenu needs to display. */
export function HeaderProfile() {
  const { session, ready } = useSession();
  const [investor, setInvestor] = useState<Investor | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);

  useEffect(() => {
    if (!session || session.role !== "investor") return;
    let cancelled = false;
    fetch("/api/investors")
      .then((r) => r.json())
      .then((data: { investors: Investor[] }) => {
        if (cancelled) return;
        setInvestor(data.investors.find((i) => i.id === session.actorId) ?? null);
      });
    fetch(`/api/investors/${session.actorId}/companies`)
      .then((r) => r.json())
      .then((data: { companies: Company[] }) => {
        if (!cancelled) setCompanies(data.companies ?? []);
      });
    return () => {
      cancelled = true;
    };
  }, [session]);

  if (!ready) return null;

  if (!session) {
    return (
      <Link href="/" className="text-sm font-medium text-navy-700 hover:text-navy-900">
        Sign in
      </Link>
    );
  }

  if (session.role === "fund-manager") {
    return <ProfileMenu />;
  }

  return (
    <ProfileMenu
      organisationId={investor?.organisationId}
      contactEmail={investor?.contactEmail}
      totalInvestmentGbp={companies.reduce((sum, c) => sum + c.investmentValueGbp, 0)}
      investmentCount={companies.length}
    />
  );
}
