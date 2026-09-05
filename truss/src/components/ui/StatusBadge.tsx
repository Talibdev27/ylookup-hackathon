import { CheckCircle2, CircleDot, AlertTriangle, Loader2, OctagonAlert } from "lucide-react";
import type { DocumentStatus } from "@/lib/types";

const CONFIG: Record<
  DocumentStatus,
  { label: string; icon: typeof CheckCircle2; classes: string }
> = {
  verified: { label: "Verified", icon: CheckCircle2, classes: "text-good bg-good-bg" },
  needs_review: { label: "Needs Review", icon: AlertTriangle, classes: "text-warn bg-warn-bg" },
  processing: { label: "Processing", icon: Loader2, classes: "text-navy-600 bg-navy-50" },
  uploaded: { label: "Uploaded", icon: CircleDot, classes: "text-ink-soft bg-paper" },
  critical: { label: "Critical", icon: OctagonAlert, classes: "text-bad bg-bad-bg" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const { label, icon: Icon, classes } = CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${classes}`}
    >
      <Icon className={`h-3.5 w-3.5 ${status === "processing" ? "animate-spin" : ""}`} />
      {label}
    </span>
  );
}
