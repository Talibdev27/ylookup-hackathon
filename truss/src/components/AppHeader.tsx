import Link from "next/link";
import type { ReactNode } from "react";

export function AppHeader({
  href = "/",
  subtitle,
  right,
}: {
  href?: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  return (
    <header className="flex items-center justify-between border-b border-line bg-white px-6 py-4 sm:px-8">
      <Link href={href} className="flex items-baseline gap-2.5">
        <span className="flex h-6 w-6 items-center justify-center rounded-[6px] bg-navy-800">
          <span className="h-2 w-2 rounded-[1.5px] bg-white" />
        </span>
        <span className="text-lg font-semibold tracking-tight text-ink">TRUSS</span>
        {subtitle && <span className="hidden text-xs text-ink-soft sm:inline">{subtitle}</span>}
      </Link>
      <div className="flex items-center gap-3">{right}</div>
    </header>
  );
}
