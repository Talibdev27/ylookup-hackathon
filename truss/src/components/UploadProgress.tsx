import { Check, Loader2 } from "lucide-react";

export const PROCESSING_STEPS = [
  "Uploading",
  "Reading document",
  "Extracting financial data",
  "Structuring spreadsheet",
  "AI validation",
  "Ready",
] as const;

export function UploadProgress({ step }: { step: number }) {
  return (
    <ol className="space-y-2.5">
      {PROCESSING_STEPS.map((label, i) => {
        const done = i < step;
        const active = i === step;
        return (
          <li key={label} className="flex items-center gap-3 text-sm">
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                done
                  ? "border-navy-800 bg-navy-800 text-white"
                  : active
                  ? "border-navy-500 text-navy-600"
                  : "border-line text-transparent"
              }`}
            >
              {done ? (
                <Check className="h-3 w-3" />
              ) : active ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : null}
            </span>
            <span className={done || active ? "text-ink" : "text-ink-soft"}>
              {label === "Ready" ? "Ready ✓" : label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
