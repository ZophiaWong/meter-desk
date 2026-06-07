import { duplicateChargeScenario } from "@/data/m1-scenario";
import Link from "next/link";

export function EvalLab() {
  const { evalSummary } = duplicateChargeScenario;

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
      <section className="mx-auto w-full max-w-5xl px-6 py-8">
        <Link className="text-sm font-medium text-meter-blue" href="/">
          Ticket Workbench
        </Link>
        <h1 className="mt-4 text-3xl font-semibold">Eval Lab</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          Static M1 preview of how Duplicate Charge evals will inspect outcome quality and trace
          behavior.
        </p>

        <article className="mt-6 rounded-md border border-meter-line bg-white p-5">
          <div className="flex flex-col gap-3 border-b border-meter-line pb-5 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-medium text-meter-blue">{evalSummary.caseId}</p>
              <h2 className="mt-2 text-xl font-semibold">{evalSummary.title}</h2>
            </div>
            <p className="rounded-full bg-[#e9f2fb] px-3 py-1 text-sm font-medium text-meter-blue">
              {evalSummary.latestRun}
            </p>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {evalSummary.dimensions.map((dimension) => (
              <section className="rounded-md border border-meter-line bg-[#fbfcfe] p-4" key={dimension.label}>
                <h3 className="text-sm font-semibold">{dimension.label}</h3>
                <p className="mt-2 text-sm font-medium text-meter-blue">{dimension.status}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{dimension.detail}</p>
              </section>
            ))}
          </div>

          <p className="mt-5 text-sm font-medium text-slate-600">{evalSummary.note}</p>
        </article>
      </section>
    </main>
  );
}
