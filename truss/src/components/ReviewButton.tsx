"use client";

import { useState } from "react";
import { Check, Flag, Loader2 } from "lucide-react";
import { useSession } from "@/lib/session";
import type { Document } from "@/lib/types";

export function ReviewButton({
  documentId,
  action,
  onDone,
}: {
  documentId: string;
  action: "approve" | "flag";
  onDone?: (doc: Document) => void;
}) {
  const { session } = useSession();
  const [loading, setLoading] = useState(false);

  const isApprove = action === "approve";

  return (
    <button
      disabled={loading}
      onClick={async () => {
        setLoading(true);
        try {
          const res = await fetch(`/api/documents/${documentId}/${action}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reviewedBy: session?.actorName }),
          });
          if (res.ok) {
            const doc = await res.json();
            onDone?.(doc);
          }
        } finally {
          setLoading(false);
        }
      }}
      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-60 ${
        isApprove ? "bg-navy-800 text-white hover:bg-navy-700" : "bg-bad-bg text-bad hover:bg-bad hover:text-white"
      }`}
    >
      {loading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : isApprove ? (
        <Check className="h-3.5 w-3.5" />
      ) : (
        <Flag className="h-3.5 w-3.5" />
      )}
      {isApprove ? "Approve" : "Flag Issue"}
    </button>
  );
}
