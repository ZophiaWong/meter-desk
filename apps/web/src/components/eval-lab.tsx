import { getEvalLabView, type EvalCaseView } from "@/lib/meterdesk-view";
import Link from "next/link";
import { rerunEvalCaseAction, runAllEvalCasesAction } from "@/lib/meterdesk-actions";
import { EvalRunControlsProvider, EvalRunForm } from "@/components/eval-run-form";

const SCENARIO_ORDER = ["Duplicate Charge", "Usage Spike", "Credit/Refund Dispute"];

export async function EvalLab() {
  try {
    const view = await getEvalLabView();
    const grouped = groupByScenario(view.cases);

    return (
      <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
        <section className="mx-auto w-full max-w-6xl px-6 py-8">
          <Link className="text-sm font-medium text-meter-blue" href="/">
            Ticket Workbench
          </Link>
          <h1 className="mt-4 text-3xl font-semibold">Eval Lab</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Run offline evals against governed agent traces. Duplicate Charge and Credit/Refund
            cases execute through governed loops; Usage Spike remains an explicit blocked coverage
            gap until its runner exists.
          </p>
          <EvalRunControlsProvider>
            <EvalRunForm
              action={runAllEvalCasesAction}
              defaultLabel="Run all evals"
              formClassName="mt-5"
              pendingLabel="Running all evals..."
              runKey="all"
              variant="primary"
            />
            <section className="mt-5 rounded-md border border-meter-line bg-white p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Latest vs baseline
                  </p>
                  <h2 className="mt-1 text-lg font-semibold">
                    Blocking pass rate {view.regressionSummary.blockingPassRate}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Baseline: {view.regressionSummary.baselineName}.{" "}
                    {view.regressionSummary.counts}.
                  </p>
                </div>
                {view.regressionSummary.latestRunHref ? (
                  <Link
                    className="rounded-md border border-meter-line px-3 py-2 text-sm font-semibold text-meter-blue"
                    href={view.regressionSummary.latestRunHref}
                  >
                    View run diff
                  </Link>
                ) : null}
              </div>
            </section>

            <div className="mt-6 space-y-6">
              {SCENARIO_ORDER.map((scenario) => (
                <section key={scenario}>
                  <h2 className="text-lg font-semibold">{scenario}</h2>
                  <div className="mt-3 grid gap-3 lg:grid-cols-3">
                    {(grouped.get(scenario) ?? []).map((evalCase) => (
                      <article
                        aria-label={evalCase.id}
                        className="rounded-md border border-meter-line bg-white p-4"
                        key={evalCase.id}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm font-medium text-meter-blue">{evalCase.id}</p>
                          <div className="flex flex-col items-end gap-2">
                            {evalCase.regressionLabel ? (
                              <span
                                className={`rounded-full px-2.5 py-1 text-xs font-semibold ${regressionClass(
                                  evalCase.regressionTone,
                                )}`}
                              >
                                {evalCase.regressionLabel}
                              </span>
                            ) : null}
                            <span
                              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(
                                evalCase.resultStatus,
                              )}`}
                            >
                              {evalCase.resultStatus}
                            </span>
                          </div>
                        </div>
                        <h3 className="mt-3 text-base font-semibold">{evalCase.title}</h3>
                        <p className="mt-2 text-sm leading-6 text-slate-600">
                          {evalCase.description}
                        </p>
                        <dl className="mt-4 space-y-2 text-xs text-slate-600">
                          <div>
                            <dt className="font-semibold text-slate-500">Expected outcome</dt>
                            <dd className="mt-1">{evalCase.expectedOutcome}</dd>
                          </div>
                          <div>
                            <dt className="font-semibold text-slate-500">Required evidence</dt>
                            <dd className="mt-1">{evalCase.requiredEvidence}</dd>
                          </div>
                          <div>
                            <dt className="font-semibold text-slate-500">Policy</dt>
                            <dd className="mt-1">{evalCase.policyRefs}</dd>
                          </div>
                          <div>
                            <dt className="font-semibold text-slate-500">Approval routing</dt>
                            <dd className="mt-1">{evalCase.approvalRouting}</dd>
                          </div>
                        </dl>
                        {evalCase.resultSummary ? (
                          <p className="mt-4 text-sm font-medium text-meter-blue">
                            {evalCase.resultSummary}
                          </p>
                        ) : null}
                        {evalCase.regressionSummary ? (
                          <p className="mt-2 text-sm leading-6 text-slate-600">
                            {evalCase.regressionSummary}
                          </p>
                        ) : null}
                        {evalCase.dimensions.length > 0 ? (
                          <ul className="mt-4 space-y-1 text-xs text-slate-600">
                            {evalCase.dimensions.map((dimension) => (
                              <li key={dimension}>{dimension}</li>
                            ))}
                          </ul>
                        ) : null}
                        <dl className="mt-4 space-y-2 text-xs text-slate-600">
                          {evalCase.failedChecks ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Failed checks</dt>
                              <dd className="mt-1">{evalCase.failedChecks}</dd>
                            </div>
                          ) : null}
                          {evalCase.missingEvidence ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Missing evidence</dt>
                              <dd className="mt-1">Missing evidence: {evalCase.missingEvidence}</dd>
                            </div>
                          ) : null}
                          {evalCase.blockedReason ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Blocked reason</dt>
                              <dd className="mt-1">{evalCase.blockedReason}</dd>
                            </div>
                          ) : null}
                          {evalCase.blockedCode ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Blocked code</dt>
                              <dd className="mt-1">Blocked code: {evalCase.blockedCode}</dd>
                            </div>
                          ) : null}
                          {evalCase.readinessGaps ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Readiness gaps</dt>
                              <dd className="mt-1">Readiness gaps: {evalCase.readinessGaps}</dd>
                            </div>
                          ) : null}
                          {evalCase.recommendedNextScenario ? (
                            <div>
                              <dt className="font-semibold text-slate-500">
                                Recommended next scenario
                              </dt>
                              <dd className="mt-1">
                                Recommended next scenario: {evalCase.recommendedNextScenario}
                              </dd>
                            </div>
                          ) : null}
                          {evalCase.complianceReasonCodes ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Compliance</dt>
                              <dd className="mt-1">
                                Compliance reason codes: {evalCase.complianceReasonCodes}
                              </dd>
                            </div>
                          ) : null}
                          {evalCase.model ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Model</dt>
                              <dd className="mt-1">Model: {evalCase.model}</dd>
                            </div>
                          ) : null}
                          {evalCase.promptVersion ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Prompt</dt>
                              <dd className="mt-1">Prompt: {evalCase.promptVersion}</dd>
                            </div>
                          ) : null}
                          {evalCase.traceRefs ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Trace refs</dt>
                              <dd className="mt-1">Trace refs: {evalCase.traceRefs}</dd>
                            </div>
                          ) : null}
                          {evalCase.judgeNotes ? (
                            <div>
                              <dt className="font-semibold text-slate-500">Judge notes</dt>
                              <dd className="mt-1">{evalCase.judgeNotes}</dd>
                            </div>
                          ) : null}
                        </dl>
                        <EvalRunForm
                          action={rerunEvalCaseAction}
                          ariaLabel={`Rerun ${evalCase.id}`}
                          defaultLabel="Rerun"
                          formClassName="mt-4"
                          hiddenFields={[{ name: "caseId", value: evalCase.id }]}
                          pendingLabel="Rerunning..."
                          runKey={evalCase.id}
                          variant="outline"
                        />
                        {evalCase.runDetailHref ? (
                          <Link
                            className="mt-3 inline-flex text-xs font-semibold text-meter-blue"
                            href={evalCase.runDetailHref}
                          >
                            View latest diff
                          </Link>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </EvalRunControlsProvider>
        </section>
      </main>
    );
  } catch (error) {
    return <EvalLabError message={error instanceof Error ? error.message : undefined} />;
  }
}

function statusClass(status: string) {
  if (status === "Passed") {
    return "bg-[#e9f8ef] text-[#166534]";
  }
  if (status === "Failed") {
    return "bg-[#fdecec] text-[#991b1b]";
  }
  if (status === "Blocked") {
    return "bg-[#fff4df] text-[#92400e]";
  }
  return "bg-[#e9f2fb] text-meter-blue";
}

function regressionClass(tone: EvalCaseView["regressionTone"]) {
  if (tone === "danger") {
    return "bg-[#fdecec] text-[#991b1b]";
  }
  if (tone === "success") {
    return "bg-[#e9f8ef] text-[#166534]";
  }
  if (tone === "warning") {
    return "bg-[#fff4df] text-[#92400e]";
  }
  if (tone === "info") {
    return "bg-[#e9f2fb] text-meter-blue";
  }
  return "bg-slate-100 text-slate-600";
}

function groupByScenario(cases: EvalCaseView[]) {
  return cases.reduce((groups, evalCase) => {
    const existing = groups.get(evalCase.scenario) ?? [];
    existing.push(evalCase);
    groups.set(evalCase.scenario, existing);
    return groups;
  }, new Map<string, EvalCaseView[]>());
}

function EvalLabError({ message }: { message?: string }) {
  return (
    <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
      <section className="mx-auto w-full max-w-5xl px-6 py-8">
        <Link className="text-sm font-medium text-meter-blue" href="/">
          Ticket Workbench
        </Link>
        <h1 className="mt-4 text-3xl font-semibold">Eval Lab</h1>
        <article className="mt-6 rounded-md border border-meter-amber bg-[#fffaf0] p-5">
          <h2 className="text-xl font-semibold">Eval data unavailable</h2>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {message ?? "FastAPI eval resources are unavailable."}
          </p>
        </article>
      </section>
    </main>
  );
}
