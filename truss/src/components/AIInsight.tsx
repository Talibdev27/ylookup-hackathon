import { AlertTriangle, Check } from "lucide-react";

export function AIInsight({ label, done, warn }: { label: string; done?: boolean; warn?: boolean }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      {warn ? (
        <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-warn" />
      ) : (
        <Check className={`h-3.5 w-3.5 shrink-0 ${done ? "text-good" : "text-line"}`} />
      )}
      <span className={warn ? "text-ink" : done ? "text-ink" : "text-ink-soft"}>{label}</span>
    </li>
  );
}
