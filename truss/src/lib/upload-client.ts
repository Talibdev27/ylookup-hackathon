// Client-side uploads to the real Python backend. A third shape alongside backend.ts
// (server-side reads) and review-client.ts (client-side JSON actions): a browser-
// initiated multipart upload with actual files, which has to run in the browser (the
// file picker lives there), so it is subject to CORS the same way review-client.ts is --
// see src/ui/app.py's after_request hook, which allows it on every /api/* path.
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:5001";

export interface StatementUploadResult {
  ok: true;
  rows: number;
  checks_applied: string[];
  flags_found: number;
}

export interface GLUploadResult {
  ok: true;
  flags_found: number;
  by_check: Record<string, number>;
}

export interface UploadError {
  error: string;
}

async function post<T>(path: string, form: FormData): Promise<T | UploadError> {
  try {
    const response = await fetch(`${BACKEND_URL}${path}`, { method: "POST", body: form });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      return { error: body?.error ?? `The backend returned ${response.status}.` };
    }
    return (body ?? { error: "The backend did not return a valid response." }) as T;
  } catch {
    // The Flask app is not running, or not reachable from here -- same treatment
    // review-client.ts and backend.ts give an unreachable backend: an honest message,
    // not a crash.
    return { error: `Could not reach the backend at ${BACKEND_URL}. Is it running?` };
  }
}

export function uploadStatements(statements: File[], workbook: File | null) {
  const form = new FormData();
  statements.forEach((file) => form.append("statements", file));
  if (workbook) form.append("workbook", workbook);
  return post<StatementUploadResult>("/api/upload", form);
}

export function uploadGLMigration(gl: File | null, loader: File | null) {
  const form = new FormData();
  if (gl) form.append("gl", gl);
  if (loader) form.append("loader", loader);
  return post<GLUploadResult>("/api/gl-migration/upload", form);
}
