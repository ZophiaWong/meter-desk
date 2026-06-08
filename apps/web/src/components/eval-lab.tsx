import { getEvalCaseViews, type EvalCaseView } from "@/lib/meterdesk-view";
import Link from "next/link";

const SCENARIO_ORDER = ["Duplicate Charge", "Usage Spike", "Credit/Refund Dispute"];

export async function EvalLab() {
  try {
    const cases = await getEvalCaseViews();
    const grouped = groupByScenario(cases);

    return (
      <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
        <section className="mx-auto w-full max-w-6xl px-6 py-8">
          <Link className="text-sm font-medium text-meter-blue" href="/">
            Ticket Workbench
          </Link>
          <h1 className="mt-4 text-3xl font-semibold">Eval Lab</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            M2 reads the seeded offline eval case catalog from FastAPI. Only the Duplicate Charge
            golden path has a static preview result before M4 graders exist.
          </p>

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
                        <span className="rounded-full bg-[#e9f2fb] px-2.5 py-1 text-xs font-semibold text-meter-blue">
                          {evalCase.resultStatus}
                        </span>
                      </div>
                      <h3 className="mt-3 text-base font-semibold">{evalCase.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{evalCase.description}</p>
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
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </section>
      </main>
    );
  } catch (error) {
    return <EvalLabError message={error instanceof Error ? error.message : undefined} />;
  }
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
