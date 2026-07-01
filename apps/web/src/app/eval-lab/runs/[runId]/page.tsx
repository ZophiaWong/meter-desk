import Link from "next/link";

import { getEvalRunComparison, type EvalRegressionCaseResource } from "@/lib/meterdesk-api";

type PageProps = {
  params: Promise<{ runId: string }>;
};

export default async function EvalRunDiffPage({ params }: PageProps) {
  const { runId } = await params;
  try {
    const comparison = await getEvalRunComparison(runId);
    return (
      <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
        <section className="mx-auto w-full max-w-6xl px-6 py-8">
          <Link className="text-sm font-medium text-meter-blue" href="/eval-lab">
            Eval Lab
          </Link>
          <h1 className="mt-4 text-3xl font-semibold">Eval Run Diff</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
            Comparing run {comparison.latest_run_id ?? runId} against{" "}
            {comparison.baseline_name ?? "the seeded baseline"}. Blocking pass rate{" "}
            {comparison.blocking_pass_rate}. {formatCounts(comparison.counts)}.
          </p>

          <div className="mt-6 space-y-4">
            {comparison.cases.map((evalCase) => (
              <article
                className="rounded-md border border-meter-line bg-white p-4"
                key={evalCase.case_id}
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p className="text-sm font-medium text-meter-blue">{evalCase.case_id}</p>
                    <h2 className="mt-2 text-lg font-semibold">{evalCase.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      {evalCase.explanations.join(" ")}
                    </p>
                  </div>
                  <span
                    className={`w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${labelClass(
                      evalCase.label,
                    )}`}
                  >
                    {formatLabel(evalCase.label)}
                  </span>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <DiffList title="Dimension changes" items={formatDimensionDiffs(evalCase)} />
                  <DiffList title="Version changes" items={formatVersionDiffs(evalCase)} />
                  <DiffList title="Trace signature" items={formatTraceDiff(evalCase)} />
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
    );
  } catch (error) {
    return (
      <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
        <section className="mx-auto w-full max-w-5xl px-6 py-8">
          <Link className="text-sm font-medium text-meter-blue" href="/eval-lab">
            Eval Lab
          </Link>
          <article className="mt-6 rounded-md border border-meter-amber bg-[#fffaf0] p-5">
            <h1 className="text-xl font-semibold">Eval run diff unavailable</h1>
            <p className="mt-3 text-sm leading-6 text-slate-700">
              {error instanceof Error
                ? error.message
                : "FastAPI eval run resources are unavailable."}
            </p>
          </article>
        </section>
      </main>
    );
  }
}

function DiffList({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">
        {(items.length > 0 ? items : ["No changes"]).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function formatCounts(counts: Record<string, number>) {
  return `${counts.regressed} regressed, ${counts.improved} improved, ${counts.unchanged} unchanged, ${counts.incomparable} incomparable, ${counts.coverage_gap} coverage gaps`;
}

function formatLabel(label: string) {
  return label
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function labelClass(label: string) {
  if (label === "regressed") {
    return "bg-[#fdecec] text-[#991b1b]";
  }
  if (label === "improved" || label === "unchanged") {
    return "bg-[#e9f8ef] text-[#166534]";
  }
  if (label === "coverage_gap") {
    return "bg-[#fff4df] text-[#92400e]";
  }
  return "bg-slate-100 text-slate-600";
}

function formatDimensionDiffs(evalCase: EvalRegressionCaseResource) {
  return evalCase.dimension_diffs.map(
    (diff) =>
      `${diff.dimension.replaceAll("_", " ")}: ${diff.baseline ?? "none"} -> ${
        diff.current ?? "none"
      }`,
  );
}

function formatVersionDiffs(evalCase: EvalRegressionCaseResource) {
  return evalCase.version_diffs.map(
    (diff) =>
      `${diff.field.replaceAll("_", " ")}: ${formatUnknown(diff.baseline)} -> ${formatUnknown(
        diff.current,
      )}`,
  );
}

function formatTraceDiff(evalCase: EvalRegressionCaseResource) {
  const added = arrayValue(evalCase.trace_diff.added_categories);
  const removed = arrayValue(evalCase.trace_diff.removed_categories);
  return [
    added.length > 0 ? `Added: ${added.join(", ")}` : null,
    removed.length > 0 ? `Removed: ${removed.join(", ")}` : null,
  ].filter((item): item is string => Boolean(item));
}

function arrayValue(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function formatUnknown(value: unknown) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return value === null || value === undefined ? "none" : String(value);
}
