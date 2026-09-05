"use client";

import { useRouter } from "next/navigation";
import { UploadDropzone } from "./UploadDropzone";
import { DocumentItem } from "./RecentUploads";
import type { Document } from "@/lib/types";

export function DocumentsBrowser({ companyId, documents }: { companyId: string; documents: Document[] }) {
  const router = useRouter();

  return (
    <div className="space-y-5">
      <UploadDropzone companyId={companyId} onUploaded={() => router.refresh()} />

      <div>
        <h2 className="mb-3 text-sm font-semibold text-ink">All Documents</h2>
        {documents.length === 0 ? (
          <p className="rounded-xl border border-dashed border-line bg-white px-4 py-6 text-center text-sm text-ink-soft">
            No documents uploaded for this company yet.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {documents.map((doc) => (
              <DocumentItem key={doc.id} doc={doc} href={`/document/${doc.id}`} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
