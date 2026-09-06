# TRUSS

The frontend: investors and fund managers upload financial documents and review what was
read out of them. Next.js App Router, talking to the Flask backend in `../src` for the
matcher's review queue and to Postgres for uploaded documents.

## Running it

```bash
npm install
npm run dev      # http://localhost:3000
```

## The database, and why there is one

Uploaded documents go to Postgres. They used to be kept in a JavaScript object for the
lifetime of the server process, which works in `npm run dev` -- one process -- and does
not work once deployed. On Vercel every route is its own serverless function, and two
requests are not guaranteed to reach the same instance: the `POST /api/documents/upload`
that created a document ran in one lambda, and the `/document/<id>` page render that
followed ran in another, which had never heard of it. The upload succeeded, the progress
bar completed, and the page 404ed on a document that existed a second earlier.

Two environment variables, in `.env.local` locally and in the Vercel project settings for
a deployment:

```
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<publishable key>
```

**Without them the app still runs**, falling back to the in-memory store and saying so
once on startup. That is a local-development convenience, not a deployment strategy: it is
the exact behaviour that produced the 404 above, so a deployment missing these variables
has the bug back.

### What is stored, and what is not

Only the things that change: `documents`, `statements`, `analyses`. Investors, fund
managers and companies are fixed seed data in `src/lib/mock-data.ts` -- nothing writes
them at runtime, so they stay in code where they can be read without a round trip.

Seed *documents* are also in code, and reads merge the two sources: a database row wins
where one exists, and a seed document that gets reviewed is copied into the database on
the way through. So an empty database is a working app rather than an empty one, and the
demo's opening state stays in version control rather than in a migration.

### Before this holds anything real

The table policies currently let the publishable key do the demo's work, because the data
is generated demo material and no client's figures are in it. For real data: drop the four
`truss_demo_*` policies and set `SUPABASE_SERVICE_ROLE_KEY` in the server environment.
`src/lib/db.ts` already prefers it, `service_role` bypasses RLS, and nothing else changes.

`src/lib/db.ts` imports `server-only`, so reaching for the store from a client component
is a build error rather than a key in the browser bundle.
