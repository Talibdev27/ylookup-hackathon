// The one honest sentence every real (non-mock) statement carries: what period this
// actually covers, and whether the books tie. See src/reports/statements.py on the
// Python side -- both statements are period movements, not a point-in-time position,
// because there is no opening balance anywhere in the underlying data.
export function StatementCaveat({ ties, note }: { ties?: boolean; note: string }) {
  return (
    <p className="rounded-xl border border-warn/30 bg-warn-bg/40 px-4 py-3 text-xs text-ink-soft">
      {ties !== undefined && (
        <span className={`mr-1.5 font-medium ${ties ? "text-good" : "text-bad"}`}>
          {ties ? "Ties." : "Does not tie."}
        </span>
      )}
      {note}
    </p>
  );
}
