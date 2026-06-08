import { getApprovalQueueItems } from "@/lib/meterdesk-view";
import Link from "next/link";

export async function ApprovalQueue() {
  try {
    const approvals = await getApprovalQueueItems();

    return (
      <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
        <section className="mx-auto w-full max-w-5xl px-6 py-8">
          <Link className="text-sm font-medium text-meter-blue" href="/">
            Ticket Workbench
          </Link>
          <h1 className="mt-4 text-3xl font-semibold">Approval Queue</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            M2 reads durable pending approval records from FastAPI. Financial action execution
            remains disabled until the governed M3 approval flow.
          </p>

          <div className="mt-6 space-y-4">
            {approvals.map((approval) => (
              <article className="rounded-md border border-meter-line bg-white p-5" key={approval.id}>
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p className="text-sm font-medium text-meter-blue">{approval.ticketId}</p>
                    <h2 className="mt-2 text-xl font-semibold">{approval.title}</h2>
                    <p className="mt-2 text-sm text-slate-600">{approval.customer}</p>
                  </div>
                  <div className="text-left md:text-right">
                    <p className="text-2xl font-semibold">{approval.amount}</p>
                    <p className="mt-1 text-sm font-medium text-meter-amber">{approval.status}</p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-700">{approval.reason}</p>
                <p className="mt-3 text-sm font-semibold text-meter-amber">{approval.blocker}</p>
                <p className="mt-2 text-xs text-slate-500">Policy: {approval.policyCitation}</p>
                <div className="mt-4 grid max-w-sm grid-cols-2 gap-2">
                  <button
                    className="h-10 rounded-md border border-meter-line bg-white text-sm font-semibold text-slate-400"
                    disabled
                    type="button"
                  >
                    Approve
                  </button>
                  <button
                    className="h-10 rounded-md border border-meter-line bg-white text-sm font-semibold text-slate-400"
                    disabled
                    type="button"
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
    );
  } catch (error) {
    return <ApprovalQueueError message={error instanceof Error ? error.message : undefined} />;
  }
}

function ApprovalQueueError({ message }: { message?: string }) {
  return (
    <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
      <section className="mx-auto w-full max-w-5xl px-6 py-8">
        <Link className="text-sm font-medium text-meter-blue" href="/">
          Ticket Workbench
        </Link>
        <h1 className="mt-4 text-3xl font-semibold">Approval Queue</h1>
        <article className="mt-6 rounded-md border border-meter-amber bg-[#fffaf0] p-5">
          <h2 className="text-xl font-semibold">Approval data unavailable</h2>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {message ?? "FastAPI approval resources are unavailable."}
          </p>
        </article>
      </section>
    </main>
  );
}
