"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { UploadProgress, PROCESSING_STEPS } from "./UploadProgress";
import type { AiAnalysis, Document, FinancialStatement } from "@/lib/types";

interface UploadResult {
  document: Document;
  statement: FinancialStatement;
  analysis: AiAnalysis;
}

export function UploadDropzone({
  companyId,
  onUploaded,
}: {
  companyId: string;
  onUploaded?: (result: UploadResult) => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const [step, setStep] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useCallback(
    async (file: File) => {
      setError(null);
      setStep(0);

      const stepTimer = setInterval(() => {
        setStep((s) => (s === null ? 0 : Math.min(s + 1, PROCESSING_STEPS.length - 2)));
      }, 350);

      try {
        const form = new FormData();
        form.append("file", file);
        form.append("companyId", companyId);

        const res = await fetch("/api/documents/upload", { method: "POST", body: form });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error ?? "Upload failed");
        }
        const result: UploadResult = await res.json();

        clearInterval(stepTimer);
        setStep(PROCESSING_STEPS.length - 1);
        setTimeout(() => {
          setStep(null);
          onUploaded?.(result);
        }, 700);
      } catch (e) {
        clearInterval(stepTimer);
        setStep(null);
        setError(e instanceof Error ? e.message : "Upload failed");
      }
    },
    [companyId, onUploaded]
  );

  if (step !== null) {
    return (
      <div className="rounded-2xl border border-line bg-white p-8">
        <UploadProgress step={step} />
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file) upload(file);
      }}
      onClick={() => inputRef.current?.click()}
      className={`group relative cursor-pointer overflow-hidden rounded-2xl border-2 border-dashed bg-white p-10 text-center transition-all ${
        dragOver ? "border-navy-600 bg-navy-50" : "border-line hover:border-navy-400"
      }`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rotate-12 rounded-3xl border border-navy-100 transition-transform group-hover:rotate-6"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-10 -left-10 h-28 w-28 -rotate-6 rounded-full border border-navy-100"
      />

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.jpg,.jpeg,.png,.xlsx,.xls,.csv"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload(file);
        }}
      />

      <div className="relative flex flex-col items-center gap-3">
        <span
          className={`flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
            dragOver ? "bg-navy-800 text-white" : "bg-navy-50 text-navy-700"
          }`}
        >
          <UploadCloud className="h-6 w-6" />
        </span>
        <div>
          <p className="font-medium text-ink">Drop your financial documents here</p>
          <p className="mt-1 text-sm text-ink-soft">PDF · JPG · PNG · Screenshots · Excel · CSV</p>
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            inputRef.current?.click();
          }}
          className="mt-1 rounded-lg bg-navy-800 px-4 py-2 text-sm font-medium text-white hover:bg-navy-700"
        >
          Browse files
        </button>
        {error && <p className="mt-1 text-xs text-bad">{error}</p>}
      </div>
    </div>
  );
}
