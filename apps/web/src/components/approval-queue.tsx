import { duplicateChargeScenario } from "@/data/m1-scenario";
import Link from "next/link";

export function ApprovalQueue() {
  const { approval, ticket } = duplicateChargeScenario;

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
      <section className="mx-auto w-full max-w-5xl px-6 py-8">
        <Link className="text-sm font-medium text-meter-blue" href="/">
          Ticket Workbench
        </Link>
        <h1 className="mt-4 text-3xl font-semibold">Approval Queue</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          M1 shows the same high-risk action as a thin queue entry. Execution remains deferred until
          later governed backend milestones.
        </p>

        <article className="mt-6 rounded-md border border-meter-line bg-white p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-medium text-meter-blue">{approval.ticketId}</p>
              <h2 className="mt-2 text-xl font-semibold">{approval.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{ticket.customer}</p>
            </div>
            <div className="text-left md:text-right">
              <p className="text-2xl font-semibold">{approval.amount}</p>
              <p className="mt-1 text-sm font-medium text-meter-amber">{approval.status}</p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-700">{approval.reason}</p>
          <p className="mt-3 text-sm font-semibold text-meter-amber">{approval.blocker}</p>
          <p className="mt-2 text-xs text-slate-500">Policy: {approval.policyCitation}</p>
        </article>
      </section>
    </main>
  );
}
