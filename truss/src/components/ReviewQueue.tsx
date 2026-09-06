"use client";

// The real analyst workflow, live against the Python matcher app: the transactions it
// was unsure about, and what the automated checks found -- not the mock AI-review flow
// under src/app/company/[companyId]/ai-review, which is a different, invented feature
// this data does not back.
import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, Loader2 } from "lucide-react";
import { formatDate } from "@/lib/format";
import {
  decideFlag,
  decideMatcherField,
  fetchReview,
  type AutomatedFlag,
  type MatcherQuestion,
  type ReviewItem,
  type ReviewResponse,
} from "@/lib/review-client";

function confidenceWord(value: number): string {
  if (value >= 0.85) return "High confidence";
  if (value >= 0.6) return "Needs a second look";
  return "Low confidence";
}

function amountLabel(raw: ReviewItem["transaction"]["raw"]): string {
  const value = raw.credit ?? raw.debit ?? 0;
  const sign = raw.credit != null ? "+" : "-";
  return `${sign}${Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${raw.currency ?? ""}`;
}

function QuestionRow({
  rowId,
  question,
  onDecided,
}: {
  rowId: number;
  question: MatcherQuestion;
  onDecided: () => void;
}) {
  const [busy, setBusy] = useState(false);

  const decide = async (choice: "approve" | "alternative", value = "") => {
    setBusy(true);
    const ok = await decideMatcherField(rowId, question.field, choice, value || question.value || "");
    setBusy(false);
    if (ok) onDecided();
  };

  if (question.decision) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-good/10 px-3 py-2 text-xs text-good">
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
        {question.label}: {question.decision.value || "marked unresolved"}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line px-3 py-2.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-xs font-medium text-ink">{question.label}</p>
        <span className="text-[11px] text-ink-soft">{confidenceWord(question.confidence)}</span>
      </div>
      <p className="mt-0.5 text-xs text-ink-soft">{question.question}</p>
      {question.value && (
        <p className="mt-1.5 text-sm font-medium text-navy-800">Proposed: {question.value}</p>
      )}
      {question.evidence?.text && (
        <p className="mt-1 text-[11px] italic text-ink-soft">{question.evidence.text}</p>
      )}
      <div className="mt-2 flex flex-wrap gap-1.5">
        <button
          disabled={busy}
          onClick={() => decide("approve")}
          className="rounded-md bg-navy-800 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-navy-700 disabled:opacity-50"
        >
          Accept
        </button>
        {question.alternatives.map((alt) => (
          <button
            key={alt.value}
            disabled={busy}
            onClick={() => decide("alternative", alt.value)}
            className="rounded-md border border-line px-2.5 py-1 text-[11px] font-medium text-ink hover:bg-navy-50 disabled:opacity-50"
          >
            Use “{alt.value}”
          </button>
        ))}
      </div>
    </div>
  );
}

function FlagRow({ flag, onDecided }: { flag: AutomatedFlag; onDecided: () => void }) {
  const [busy, setBusy] = useState(false);

  const decide = async (action: "acknowledge" | "resolved" | "false_positive") => {
    setBusy(true);
    const ok = await decideFlag(flag.flag_id, action);
    setBusy(false);
    if (ok) onDecided();
  };

  const critical = flag.severity === "error";

  if (flag.decision) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-good/10 px-3 py-2 text-xs text-good">
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
        {flag.label}: {flag.decision.action}
      </div>
    );
  }

  return (
    <div className={`rounded-lg border px-3 py-2.5 ${critical ? "border-bad/30 bg-bad-bg/40" : "border-warn/30 bg-warn-bg/40"}`}>
      <div className="flex items-center gap-1.5">
        <CircleAlert className={`h-3.5 w-3.5 ${critical ? "text-bad" : "text-warn"}`} />
        <p className={`text-xs font-medium ${critical ? "text-bad" : "text-ink"}`}>
          {flag.label} — {flag.severity_label}
        </p>
      </div>
      <p className="mt-1 text-xs text-ink-soft">{flag.message}</p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        <button
          disabled={busy}
          onClick={() => decide("acknowledge")}
          className="rounded-md bg-navy-800 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-navy-700 disabled:opacity-50"
        >
          Acknowledge
        </button>
        <button
          disabled={busy}
          onClick={() => decide("false_positive")}
          className="rounded-md border border-line px-2.5 py-1 text-[11px] font-medium text-ink hover:bg-navy-50 disabled:opacity-50"
        >
          Not an issue
        </button>
      </div>
    </div>
  );
}

export function ReviewQueue({ companyId }: { companyId: string }) {
  const [data, setData] = useState<ReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notConfigured, setNotConfigured] = useState(false);

  const load = useCallback(() => {
    // No synchronous setLoading(true) here: the initial state is already `true`, and a
    // reload after accepting a proposal should update the list in place rather than
    // flash a full loading state for what is normally a sub-second re-fetch.
    fetchReview(companyId).then((result) => {
      setData(result);
      setNotConfigured(result === null);
      setLoading(false);
    });
  }, [companyId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-line bg-white px-5 py-10 text-sm text-ink-soft">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading the review queue…
      </div>
    );
  }

  if (notConfigured || !data) {
    return (
      <div className="rounded-2xl border border-dashed border-line bg-white px-6 py-16 text-center text-sm text-ink-soft">
        No live review queue for this company. Either the Flask matcher app is not
        running at the configured
        <code className="mx-1 rounded bg-paper px-1.5 py-0.5 text-xs">NEXT_PUBLIC_BACKEND_URL</code>
        , or this company has no matcher data behind it.
      </div>
    );
  }

  const nothingOpen = data.items.length === 0 && data.unattached_flags.length === 0;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-line bg-white px-5 py-4">
        <div>
          <p className="text-sm font-medium text-ink">
            {data.summary.total_review_items_remaining} of {data.summary.total_review_items} review items open
          </p>
          <p className="text-xs text-ink-soft">
            {data.checks.checks_executed}/{data.checks.checks_total} automated checks ran ·{" "}
            {data.checks.flags_found} finding(s)
          </p>
        </div>
      </div>

      {nothingOpen && (
        <div className="flex items-center gap-2 rounded-2xl border border-line bg-good/10 px-5 py-6 text-sm text-good">
          <CheckCircle2 className="h-4 w-4" /> Nothing left to check for this fund.
        </div>
      )}

      {data.unattached_flags.map((flag) => (
        <FlagRow key={flag.flag_id} flag={flag} onDecided={load} />
      ))}

      {data.items.map((item) => (
        <div key={item.transaction.row_id} className="rounded-2xl border border-line bg-white p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-sm font-medium text-ink">{amountLabel(item.transaction.raw)}</p>
            <span className="text-xs text-ink-soft">
              {item.transaction.raw.value_date ? formatDate(item.transaction.raw.value_date) : ""} ·{" "}
              {item.transaction.source.pdf}
              {item.transaction.source.page ? `, p.${item.transaction.source.page}` : ""}
            </span>
          </div>
          {item.transaction.raw.narrative_raw && (
            <p className="mt-1.5 rounded-lg bg-paper px-3 py-2 text-xs text-ink-soft">
              {item.transaction.raw.narrative_raw}
            </p>
          )}
          <div className="mt-3 space-y-2">
            {item.matcher_questions.map((question) => (
              <QuestionRow
                key={question.field}
                rowId={item.transaction.row_id}
                question={question}
                onDecided={load}
              />
            ))}
            {item.automated_flags.map((flag) => (
              <FlagRow key={flag.flag_id} flag={flag} onDecided={load} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
