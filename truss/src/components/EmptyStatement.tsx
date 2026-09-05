import Link from "next/link";
import { FileStack } from "lucide-react";

export function EmptyStatement({ label, companyId }: { label: string; companyId: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-line bg-white px-6 py-16 text-center">
      <FileStack className="h-8 w-8 text-line" />
      <p className="text-sm font-medium text-ink">No {label} yet</p>
      <p className="max-w-xs text-xs text-ink-soft">
        Upload a document and TRUSS will classify it and structure it here automatically.
      </p>
      <Link
        href={`/company/${companyId}/documents`}
        className="mt-1 rounded-lg bg-navy-800 px-3.5 py-2 text-xs font-medium text-white hover:bg-navy-700"
      >
        Upload Document
      </Link>
    </div>
  );
}
