import { getApprovalQueueItems, type ApprovalQueueStatus } from "@/lib/meterdesk-view";
import { approveRequestAction, rejectRequestAction } from "@/lib/meterdesk-actions";
import Link from "next/link";

const STATUSES: ApprovalQueueStatus[] = ["pending", "approved", "rejected", "all"];

export async function ApprovalQueue({ status = "pending" }: { status?: ApprovalQueueStatus }) {
  try {
    const approvals = await getApprovalQueueItems(status);

    return (
      <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
        <section className="mx-auto w-full max-w-5xl px-6 py-8">
          <Link className="text-sm font-medium text-meter-blue" href="/">
            Ticket Workbench
          </Link>
          <h1 className="mt-4 text-3xl font-semibold">Approval Queue</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Pending financial actions stay blocked until a human reviewer approves or rejects them.
          </p>
          <nav aria-label="Approval status" className="mt-5 flex flex-wrap gap-2">
            {STATUSES.map((item) => (
              <Link
                className={`inline-flex h-9 items-center rounded-md border px-3 text-sm font-medium ${
                  item === status
                    ? "border-meter-blue bg-[#e9f2fb] text-meter-blue"
                    : "border-meter-line bg-white text-slate-600"
                }`}
                href={`/approvals?status=${item}`}
                key={item}
              >
                {titleCase(item)}
              </Link>
            ))}
          </nav>

          <div className="mt-6 space-y-4">
            {approvals.map((approval) => {
              const isPending = approval.status.toLowerCase() === "pending";
              return (
                <article
                  className="rounded-md border border-meter-line bg-white p-5"
                  key={approval.id}
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="text-sm font-medium text-meter-blue">{approval.ticketId}</p>
                      <h2 className="mt-2 text-xl font-semibold">{approval.title}</h2>
                      <p className="mt-2 text-sm text-slate-600">{approval.customer}</p>
                    </div>
                    <div className="text-left md:text-right">
                      <p className="text-2xl font-semibold">{approval.amount}</p>
                      <p className="mt-1 text-sm font-medium text-meter-amber">
                        {approval.status}
                      </p>
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-slate-700">{approval.reason}</p>
                  <p className="mt-3 text-sm font-semibold text-meter-amber">{approval.blocker}</p>
                  <p className="mt-2 text-xs text-slate-500">Policy: {approval.policyCitation}</p>
                  <div className="mt-4 grid max-w-sm grid-cols-2 gap-2">
                    <form action={approveRequestAction}>
                      <input name="approvalId" type="hidden" value={approval.id} />
                      <button
                        className="h-10 w-full rounded-md border border-meter-line bg-white text-sm font-semibold text-meter-blue disabled:text-slate-400"
                        disabled={!isPending}
                        type="submit"
                      >
                        Approve
                      </button>
                    </form>
                    <form action={rejectRequestAction}>
                      <input name="approvalId" type="hidden" value={approval.id} />
                      <button
                        className="h-10 w-full rounded-md border border-meter-line bg-white text-sm font-semibold text-meter-amber disabled:text-slate-400"
                        disabled={!isPending}
                        type="submit"
                      >
                        Reject
                      </button>
                    </form>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </main>
    );
  } catch (error) {
    return <ApprovalQueueError message={error instanceof Error ? error.message : undefined} />;
  }
}

function titleCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
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
