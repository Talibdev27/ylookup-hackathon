"use client";

import { useState } from "react";
import { Eye } from "lucide-react";

export function ViewSourceButton({ sourceFileNote }: { sourceFileNote: string }) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-navy-500 hover:text-navy-800"
      >
        <Eye className="h-3.5 w-3.5" />
        View Source
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-1 w-64 rounded-lg border border-line bg-white p-3 text-xs shadow-card">
            <p className="font-medium text-ink">Original document</p>
            <p className="mt-1 text-ink-soft">{sourceFileNote}</p>
            <p className="mt-2 text-ink-soft">
              TRUSS keeps the generated spreadsheet as the primary view — the original file
              viewer is not wired up in this build.
            </p>
          </div>
        </>
      )}
    </span>
  );
}
