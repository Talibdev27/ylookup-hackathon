export function formatGbp(value: number): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 0,
  }).format(value);
}

/** £2,800,000 -> "£2.8M", £482,000 -> "£482,000" (PRD examples keep sub-£1M values exact). */
export function formatGbpCompact(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) {
    return `${value < 0 ? "-" : ""}£${(abs / 1_000_000).toFixed(1)}M`;
  }
  if (abs >= 100_000) {
    return `${value < 0 ? "-" : ""}£${Math.round(abs / 1000)}K`;
  }
  return formatGbp(value);
}

export function formatPercentChange(current: number, previous: number): string {
  if (previous === 0) return "—";
  const pct = ((current - previous) / Math.abs(previous)) * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(d);
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}
