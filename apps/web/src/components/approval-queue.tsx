import { getApprovalQueueItems, type ApprovalQueueStatus } from "@/lib/meterdesk-view";
import { approveRequestAction, rejectRequestAction } from "@/lib/meterdesk-actions";
import {
  APPROVAL_PERMISSION_EXPLANATION,
  canDecideApproval,
  type DemoPrincipal,
} from "@/lib/demo-auth";
import { handleProtectedApiError } from "@/lib/session";
import Link from "next/link";

const STATUSES: ApprovalQueueStatus[] = ["pending", "approved", "rejected", "all"];

type ApprovalQueueProps = {
  accessToken: string;
  currentPrincipal: DemoPrincipal;
  status?: ApprovalQueueStatus;
};

export async function ApprovalQueue({
  accessToken,
  currentPrincipal,
  status = "pending",
}: ApprovalQueueProps) {
  try {
    const approvals = await getApprovalQueueItems(status, accessToken);
    const canDecide = canDecideApproval(currentPrincipal);

    return (
      <section className="mx-auto w-full max-w-5xl">
        <h1 className="text-3xl font-semibold">Approval Queue</h1>
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
                {approval.decisionActorSummary ? (
                  <div className="mt-3 rounded-md border border-meter-line bg-[#fbfcfe] p-3 text-xs text-slate-600">
                    <p className="font-semibold text-slate-800">
                      Decided by {approval.decisionActorSummary}
                    </p>
                    {approval.decisionNote ? <p className="mt-1">{approval.decisionNote}</p> : null}
                  </div>
                ) : null}
                <div className="mt-4 grid max-w-sm grid-cols-2 gap-2">
                  <form action={approveRequestAction}>
                    <input name="approvalId" type="hidden" value={approval.id} />
                    <button
                      className="h-10 w-full rounded-md border border-meter-line bg-white text-sm font-semibold text-meter-blue disabled:cursor-not-allowed disabled:text-slate-400"
                      disabled={!isPending || !canDecide}
                      title={!canDecide ? APPROVAL_PERMISSION_EXPLANATION : undefined}
                      type="submit"
                    >
                      Approve
                    </button>
                  </form>
                  <form action={rejectRequestAction}>
                    <input name="approvalId" type="hidden" value={approval.id} />
                    <button
                      className="h-10 w-full rounded-md border border-meter-line bg-white text-sm font-semibold text-meter-amber disabled:cursor-not-allowed disabled:text-slate-400"
                      disabled={!isPending || !canDecide}
                      title={!canDecide ? APPROVAL_PERMISSION_EXPLANATION : undefined}
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
    );
  } catch (error) {
    const returnTo = status === "pending" ? "/approvals" : `/approvals?status=${status}`;
    handleProtectedApiError(error, returnTo);
    return <ApprovalQueueError message={error instanceof Error ? error.message : undefined} />;
  }
}

function titleCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function ApprovalQueueError({ message }: { message?: string }) {
  return (
    <section className="mx-auto w-full max-w-5xl">
      <h1 className="text-3xl font-semibold">Approval Queue</h1>
      <article className="mt-6 rounded-md border border-meter-amber bg-[#fffaf0] p-5">
        <h2 className="text-xl font-semibold">Approval data unavailable</h2>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          {message ?? "FastAPI approval resources are unavailable."}
        </p>
      </article>
    </section>
  );
}
