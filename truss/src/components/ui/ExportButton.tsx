import { Download } from "lucide-react";

export function ExportButton({ documentId }: { documentId: string }) {
  return (
    <a
      href={`/api/documents/${documentId}/excel`}
      download
      className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-navy-500 hover:text-navy-800"
    >
      <Download className="h-3.5 w-3.5" />
      Export Excel
    </a>
  );
}
