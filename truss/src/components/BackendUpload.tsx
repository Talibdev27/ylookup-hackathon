"use client";

// Real uploads for the four funds the Python matcher app actually knows about -- not the
// mock `UploadDropzone` under DocumentsBrowser, which posts to this app's own
// `/api/documents/upload` and returns fabricated data (see that route's own comment).
// This posts to the Flask backend directly and shows back what it actually found.
//
// Uploads here are dataset-wide, not scoped to one company: the reference workbook and
// statements cover every fund the matcher knows, and the GL/loader pair is its own
// separate dataset. `companyId` is only used to link back to that company's own review
// queue afterward.
import { useRouter } from "next/navigation";
import { useState } from "react";
import { CheckCircle2, Loader2, UploadCloud } from "lucide-react";
import {
  uploadGLMigration,
  uploadStatements,
  type GLUploadResult,
  type StatementUploadResult,
  type UploadError,
} from "@/lib/upload-client";

function isError<T>(result: T | UploadError): result is UploadError {
  return typeof result === "object" && result !== null && "error" in result;
}

function StatementUploadCard({ companyId }: { companyId: string }) {
  const router = useRouter();
  const [statements, setStatements] = useState<File[]>([]);
  const [workbook, setWorkbook] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StatementUploadResult | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    const outcome = await uploadStatements(statements, workbook);
    setBusy(false);
    if (isError(outcome)) {
      setError(outcome.error);
      return;
    }
    setResult(outcome);
    setStatements([]);
    setWorkbook(null);
    router.refresh();
  };

  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <h3 className="text-sm font-semibold text-ink">Bank statements</h3>
      <p className="mt-1 text-xs text-ink-soft">
        This week&apos;s statements (PDF), and a reference workbook if one is not already
        set up. Runs the real matcher and every automated check.
      </p>

      <label className="mt-4 block text-xs font-medium text-ink">
        Statements (PDF, one or more)
        <input
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="mt-1.5 block w-full text-xs text-ink-soft file:mr-3 file:rounded-md file:border file:border-line file:bg-paper file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink"
          onChange={(e) => setStatements(Array.from(e.target.files ?? []))}
        />
      </label>

      <label className="mt-3 block text-xs font-medium text-ink">
        Reference workbook (.xlsx) — optional if already set up
        <input
          type="file"
          accept=".xlsx,.xlsm"
          className="mt-1.5 block w-full text-xs text-ink-soft file:mr-3 file:rounded-md file:border file:border-line file:bg-paper file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink"
          onChange={(e) => setWorkbook(e.target.files?.[0] ?? null)}
        />
      </label>

      <button
        type="button"
        disabled={busy || statements.length === 0}
        onClick={submit}
        className="mt-4 inline-flex items-center gap-2 rounded-md bg-navy-800 px-3.5 py-2 text-xs font-medium text-white hover:bg-navy-700 disabled:opacity-50"
      >
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UploadCloud className="h-3.5 w-3.5" />}
        Run the matcher
      </button>

      {error && <p className="mt-3 text-xs text-bad">{error}</p>}
      {result && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-good-bg px-3 py-2.5 text-xs text-good">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            {result.rows} rows processed, {result.checks_applied.length} checks ran,{" "}
            {result.flags_found} finding(s).{" "}
            <a href={`/company/${companyId}/review`} className="underline">
              Open the review queue
            </a>
            .
          </span>
        </div>
      )}
    </div>
  );
}

function GLUploadCard() {
  const [gl, setGl] = useState<File | null>(null);
  const [loader, setLoader] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GLUploadResult | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    const outcome = await uploadGLMigration(gl, loader);
    setBusy(false);
    if (isError(outcome)) {
      setError(outcome.error);
      return;
    }
    setResult(outcome);
    setGl(null);
    setLoader(null);
  };

  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <h3 className="text-sm font-semibold text-ink">GL → loader migration</h3>
      <p className="mt-1 text-xs text-ink-soft">
        A separate dataset: the investor-level general ledger and the loader/upload
        template it maps to. Either file alone leaves the other as it was.
      </p>

      <label className="mt-4 block text-xs font-medium text-ink">
        Investor-level GL (.xlsx)
        <input
          type="file"
          accept=".xlsx,.xlsm"
          className="mt-1.5 block w-full text-xs text-ink-soft file:mr-3 file:rounded-md file:border file:border-line file:bg-paper file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink"
          onChange={(e) => setGl(e.target.files?.[0] ?? null)}
        />
      </label>

      <label className="mt-3 block text-xs font-medium text-ink">
        Loader / upload template (.xlsx)
        <input
          type="file"
          accept=".xlsx,.xlsm"
          className="mt-1.5 block w-full text-xs text-ink-soft file:mr-3 file:rounded-md file:border file:border-line file:bg-paper file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-ink"
          onChange={(e) => setLoader(e.target.files?.[0] ?? null)}
        />
      </label>

      <button
        type="button"
        disabled={busy || (!gl && !loader)}
        onClick={submit}
        className="mt-4 inline-flex items-center gap-2 rounded-md bg-navy-800 px-3.5 py-2 text-xs font-medium text-white hover:bg-navy-700 disabled:opacity-50"
      >
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UploadCloud className="h-3.5 w-3.5" />}
        Run the checks
      </button>

      {error && <p className="mt-3 text-xs text-bad">{error}</p>}
      {result && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-good-bg px-3 py-2.5 text-xs text-good">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{result.flags_found} finding(s) across {Object.keys(result.by_check).length} checks.</span>
        </div>
      )}
    </div>
  );
}

export function BackendUpload({ companyId }: { companyId: string }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <StatementUploadCard companyId={companyId} />
      <GLUploadCard />
    </div>
  );
}
