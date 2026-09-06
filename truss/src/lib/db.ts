import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * The Postgres connection behind the document store.
 *
 * Uploaded documents used to live in a process-lifetime object. That works in `next dev`,
 * which is one process, and does not work on Vercel, where every route is its own
 * serverless function and two requests are not guaranteed to reach the same instance: the
 * POST that created a document and the page render that read it back ran in different
 * lambdas, so the page 404ed on a document that had just uploaded successfully.
 *
 * `server-only` is load-bearing rather than decorative. It makes importing this file from
 * a client component a build error, which is what keeps a key out of the browser bundle
 * if somebody later reaches for the store from the client.
 */

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;

// The service key bypasses RLS and never reaches the browser. It is preferred when set;
// the publishable key is what the demo runs on, and the table policies are scoped to
// exactly what the demo does. See the migration for how to lock this down.
const key =
  process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let cached: SupabaseClient | null = null;

/** The client, or null when no database is configured. */
export function db(): SupabaseClient | null {
  if (!url || !key) return null;
  if (!cached) {
    cached = createClient(url, key, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
  }
  return cached;
}

/**
 * Why the store fell back to memory, in words a developer reads in their terminal.
 * Returns null when the database is configured, so callers can use it as the reason.
 */
export function misconfiguration(): string | null {
  if (url && key) return null;
  const missing = [
    !url && "NEXT_PUBLIC_SUPABASE_URL",
    !key && "NEXT_PUBLIC_SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY)",
  ].filter(Boolean);
  return `${missing.join(" and ")} not set`;
}
