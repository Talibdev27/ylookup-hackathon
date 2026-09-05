import Link from "next/link";
import type { Document } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { StatusBadge } from "./ui/StatusBadge";

const FORMAT_LABEL: Record<Document["sourceFormat"], string> = {
  pdf: "PDF",
  jpg: "JPG",
  png: "PNG",
  screenshot: "Screenshot",
  excel: "Excel",
  csv: "CSV",
};

export function RecentUploads({
  companyId,
  documents,
  activeDocumentId,
}: {
  companyId: string;
  documents: Document[];
  activeDocumentId?: string;
}) {
  return (
    <div>
      <h2 className="px-1 text-sm font-semibold text-ink">Recent Uploads</h2>
      {documents.length === 0 ? (
        <p className="mt-3 rounded-lg border border-dashed border-line px-3 py-4 text-xs text-ink-soft">
          Nothing uploaded yet.
        </p>
      ) : (
        <ul className="mt-3 space-y-1.5">
          {documents.slice(0, 10).map((doc) => (
            <li key={doc.id}>
              <DocumentItem doc={doc} href={`/document/${doc.id}`} active={doc.id === activeDocumentId} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function DocumentItem({
  doc,
  href,
  active,
}: {
  doc: Document;
  href: string;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`block rounded-lg border px-3 py-2.5 transition-colors ${
        active ? "border-navy-500 bg-navy-50" : "border-line bg-white hover:border-navy-400"
      }`}
    >
      <p className="truncate text-sm font-medium text-ink">{doc.name}</p>
      <p className="mt-0.5 text-xs text-ink-soft">
        {formatDate(doc.uploadedAt)} · Source: {FORMAT_LABEL[doc.sourceFormat]}
      </p>
      <div className="mt-1.5">
        <StatusBadge status={doc.status} />
      </div>
    </Link>
  );
}
