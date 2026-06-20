import type { WorkbenchScenario } from "@/lib/meterdesk-view";
import {
  approveRequestAction,
  rejectRequestAction,
  startDefaultAgentRunAction,
} from "@/lib/meterdesk-actions";
import type { ReactNode } from "react";

type TicketWorkbenchProps = {
  scenario: WorkbenchScenario;
};

export function TicketWorkbench({ scenario }: TicketWorkbenchProps) {
  return (
    <div className="grid gap-5 py-6 xl:grid-cols-[260px_minmax(0,1fr)_360px]">
      <aside className="rounded-md border border-meter-line bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase text-slate-500">Tickets</h2>
          <span className="rounded-full bg-[#e9f2fb] px-2.5 py-1 text-xs font-medium text-meter-blue">
            M3 API
          </span>
        </div>
        <div className="mt-4 space-y-3">
          {scenario.tickets.map((ticket) => (
            <article
              className={`rounded-md border p-3 ${
                ticket.isActive
                  ? "border-meter-blue bg-[#f7fbff]"
                  : "border-meter-line bg-[#f8fafc] text-slate-500"
              }`}
              key={ticket.id}
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-semibold">{ticket.title}</h3>
                <span className="text-xs font-medium">{ticket.id}</span>
              </div>
              <p className="mt-2 text-sm">{ticket.customer}</p>
              <p className="mt-3 text-xs font-medium uppercase text-slate-500">{ticket.status}</p>
              <p className="mt-2 text-xs leading-5 text-slate-500">{ticket.summary}</p>
            </article>
          ))}
        </div>
      </aside>

      <section className="min-w-0 rounded-md border border-meter-line bg-white p-5">
        <div className="flex flex-col gap-4 border-b border-meter-line pb-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-meter-blue">{scenario.ticket.id}</p>
            <h1 className="mt-2 text-3xl font-semibold leading-tight">
              {scenario.ticket.title}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
              {scenario.ticket.summary}
            </p>
          </div>
          <div className="rounded-md border border-meter-line bg-[#fbfcfe] px-4 py-3 text-sm">
            <p className="font-semibold">{scenario.ticket.customer}</p>
            <p className="mt-1 text-slate-500">{scenario.ticket.severity}</p>
            <p className="mt-1 text-slate-500">Opened {scenario.ticket.openedAt}</p>
          </div>
        </div>

        <section aria-labelledby="billing-evidence-heading" className="mt-5" role="region">
          <h2 id="billing-evidence-heading" className="text-lg font-semibold">
            Billing evidence
          </h2>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <EvidencePanel title="Account">
              <KeyValue label="Customer" value={scenario.evidence.account.name} />
              <KeyValue label="Plan" value={scenario.evidence.account.plan} />
              <KeyValue label="Owner" value={scenario.evidence.account.owner} />
              <KeyValue label="State" value={scenario.evidence.account.status} />
            </EvidencePanel>

            <EvidencePanel title="Invoice">
              <KeyValue label="Invoice" value={scenario.evidence.invoice.id} />
              <KeyValue label="Period" value={scenario.evidence.invoice.period} />
              <KeyValue label="Total" value={scenario.evidence.invoice.total} />
              <KeyValue label="Status" value={scenario.evidence.invoice.status} />
            </EvidencePanel>
          </div>

          <div className="mt-4 rounded-md border border-meter-line">
            <div className="grid grid-cols-[1fr_0.6fr_0.7fr] border-b border-meter-line bg-[#f8fafc] px-4 py-3 text-xs font-semibold uppercase text-slate-500">
              <span>Charge</span>
              <span>Amount</span>
              <span>Status</span>
            </div>
            {scenario.evidence.charges.map((charge) => (
              <div
                className="grid grid-cols-[1fr_0.6fr_0.7fr] gap-3 border-b border-meter-line px-4 py-3 text-sm last:border-b-0"
                key={charge.id}
              >
                <div>
                  <p className="font-medium">{charge.id}</p>
                  <p className="mt-1 text-xs text-slate-500">{charge.capturedAt}</p>
                </div>
                <p className="font-semibold">{charge.amount}</p>
                <div>
                  <p>{charge.status}</p>
                  <p className="mt-1 text-xs text-slate-500">{charge.processorState}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <EvidencePanel title="Credit ledger">
              <p className="font-semibold">{scenario.evidence.credits.label}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{scenario.evidence.credits.detail}</p>
            </EvidencePanel>
            <EvidencePanel title="Usage summary">
              <p className="font-semibold">{scenario.evidence.usage.label}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{scenario.evidence.usage.detail}</p>
            </EvidencePanel>
            <EvidencePanel title="Policy citation">
              <p className="font-semibold">{scenario.evidence.policy.id}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{scenario.evidence.policy.reason}</p>
            </EvidencePanel>
          </div>
        </section>

        <section className="mt-5 rounded-md border border-meter-line bg-[#fbfcfe] p-4">
          <h2 className="text-lg font-semibold">Internal resolution</h2>
          {scenario.drafts ? (
            <p className="mt-3 text-sm leading-6 text-slate-700">
              {scenario.drafts.internalResolution}
            </p>
          ) : (
            <div className="mt-3 flex flex-col gap-3 text-sm leading-6 text-slate-700">
              <p>No internal resolution yet</p>
            </div>
          )}
          <p className="mt-3 text-sm font-medium text-meter-blue">{scenario.ticket.outcome}</p>
        </section>
      </section>

      <section
        aria-labelledby="governance-heading"
        className="rounded-md border border-meter-line bg-white p-5"
        role="region"
      >
        <h2 id="governance-heading" className="text-lg font-semibold">
          Governance and trace
        </h2>
        <GovernanceRulesDrawer scenario={scenario} />
        <RunStateCard scenario={scenario} />
        <ApprovalCard scenario={scenario} />
        <MutationResultList scenario={scenario} />
        <TraceTimeline traces={scenario.traces} />
        <DraftReply scenario={scenario} />
      </section>
    </div>
  );
}

function EvidencePanel({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-md border border-meter-line bg-[#fbfcfe] p-4">
      <h3 className="text-sm font-semibold uppercase text-slate-500">{title}</h3>
      <div className="mt-3 space-y-3 text-sm">{children}</div>
    </section>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}

function ApprovalCard({ scenario }: TicketWorkbenchProps) {
  if (!scenario.approval) {
    return (
      <section className="mt-4 rounded-md border border-meter-line bg-[#fbfcfe] p-4">
        <p className="text-xs font-semibold uppercase text-slate-500">No approval request</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Financial action approval appears after a governed agent run proposes a refund or credit.
        </p>
      </section>
    );
  }
  const isPending = scenario.approval.status.toLowerCase() === "pending";
  const tone = approvalToneClass(scenario.approval.status);

  return (
    <section className={`mt-4 rounded-md border p-4 ${tone.panel}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={`text-xs font-semibold uppercase ${tone.label}`}>
            {scenario.approval.status}
          </p>
          <h3 className="mt-2 text-base font-semibold">{scenario.approval.title}</h3>
        </div>
        <span className="text-lg font-semibold">{scenario.approval.amount}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{scenario.approval.reason}</p>
      <p className={`mt-3 text-sm font-medium ${tone.label}`}>{scenario.approval.blocker}</p>
      <p className="mt-2 text-xs text-slate-500">Policy: {scenario.approval.policyCitation}</p>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <form action={approveRequestAction}>
          <input name="approvalId" type="hidden" value={scenario.approval.id} />
          <button
            className="h-10 w-full rounded-md border border-meter-line bg-white text-sm font-semibold text-meter-blue disabled:text-slate-400"
            disabled={!isPending}
            type="submit"
          >
            Approve
          </button>
        </form>
        <form action={rejectRequestAction}>
          <input name="approvalId" type="hidden" value={scenario.approval.id} />
          <button
            className="h-10 w-full rounded-md border border-meter-line bg-white text-sm font-semibold text-meter-amber disabled:text-slate-400"
            disabled={!isPending}
            type="submit"
          >
            Reject
          </button>
        </form>
      </div>
    </section>
  );
}

function RunStateCard({ scenario }: TicketWorkbenchProps) {
  const failed = scenario.run?.status.toLowerCase() === "failed";

  return (
    <section
      className={`mt-4 rounded-md border p-4 ${
        failed ? "border-meter-amber bg-[#fffaf0]" : "border-meter-line bg-[#fbfcfe]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Agent run</p>
          <h3 className="mt-2 text-base font-semibold">
            {scenario.run ? scenario.run.status : "No agent run yet"}
          </h3>
          {scenario.run ? <p className="mt-1 text-xs text-slate-500">{scenario.run.id}</p> : null}
        </div>
        {scenario.run?.model ? (
          <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">
            {scenario.run.model}
          </span>
        ) : null}
      </div>
      {scenario.run?.promptVersion ? (
        <p className="mt-3 text-xs text-slate-500">Prompt: {scenario.run.promptVersion}</p>
      ) : null}
      {scenario.run?.errorState ? (
        <p className="mt-3 text-sm font-medium text-meter-amber">{scenario.run.errorState}</p>
      ) : null}
      {!scenario.run ? (
        <form action={startDefaultAgentRunAction} className="mt-4">
          <button
            className="h-10 rounded-md bg-meter-blue px-4 text-sm font-semibold text-white"
            type="submit"
          >
            Run investigation
          </button>
        </form>
      ) : null}
    </section>
  );
}

function MutationResultList({ scenario }: TicketWorkbenchProps) {
  if (scenario.mutations.length === 0) {
    return (
      <section className="mt-4 rounded-md border border-meter-line bg-[#fbfcfe] p-4">
        <h3 className="text-sm font-semibold uppercase text-slate-500">Mock mutation</h3>
        <p className="mt-3 text-sm leading-6 text-slate-600">No mock mutation executed</p>
      </section>
    );
  }
  return (
    <section className="mt-4 rounded-md border border-meter-mint bg-[#f0fdf8] p-4">
      <h3 className="text-sm font-semibold uppercase text-slate-500">Mock mutation</h3>
      <div className="mt-3 space-y-3">
        {scenario.mutations.map((mutation) => (
          <article className="text-sm leading-6 text-slate-700" key={mutation.id}>
            <div className="flex items-start justify-between gap-3">
              <p className="font-semibold">{mutation.id}</p>
              <span className="font-semibold text-meter-mint">{mutation.amount}</span>
            </div>
            <p>{mutation.reason}</p>
            <p className="text-xs text-slate-500">
              {mutation.status} on {mutation.executedAt}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function TraceTimeline({ traces }: { traces: WorkbenchScenario["traces"] }) {
  return (
    <section className="mt-5">
      <h3 className="text-sm font-semibold uppercase text-slate-500">Trace timeline</h3>
      {traces.length === 0 ? (
        <p className="mt-3 rounded-md border border-meter-line bg-[#fbfcfe] p-3 text-sm text-slate-600">
          No trace entries yet
        </p>
      ) : null}
      <ol className="mt-3 space-y-3">
        {traces.map((trace) => (
          <li className="rounded-md border border-meter-line bg-[#fbfcfe] p-3" key={trace.id}>
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold">{trace.category}</p>
              <span className="rounded-full bg-white px-2 py-1 text-xs font-medium text-slate-600">
                {trace.risk} risk
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-700">{trace.label}</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">{trace.output}</p>
            {trace.governance ? (
              <p className="mt-2 text-xs font-medium text-slate-500">{trace.governance}</p>
            ) : null}
            <p className="mt-2 text-xs font-medium text-meter-blue">{trace.evidence}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function GovernanceRulesDrawer({ scenario }: TicketWorkbenchProps) {
  const policyCount = scenario.toolPolicies.length;
  const highRiskCount = scenario.toolPolicies.filter((policy) => policy.risk === "High").length;

  return (
    <details className="mt-3 rounded-md border border-meter-line bg-[#fbfcfe] p-3">
      <summary className="cursor-pointer list-none text-sm font-semibold text-meter-blue">
        {policyCount} governed actions | {highRiskCount} high-risk gate | View rules
      </summary>
      <div className="mt-4 space-y-3">
        <p className="text-xs leading-5 text-slate-500">
          Read-only matrix generated from the backend code-first registry.
        </p>
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-2 text-left text-xs">
            <thead className="text-slate-500">
              <tr>
                <th className="pr-3 font-semibold">Action</th>
                <th className="pr-3 font-semibold">Risk</th>
                <th className="pr-3 font-semibold">Gate</th>
                <th className="font-semibold">Refs</th>
              </tr>
            </thead>
            <tbody>
              {scenario.toolPolicies.map((policy) => (
                <tr className="align-top" key={policy.id}>
                  <td className="pr-3">
                    <p className="font-semibold text-slate-800">{policy.id}</p>
                    <p className="mt-1 text-slate-500">{policy.label}</p>
                  </td>
                  <td className="pr-3 font-semibold">{policy.risk}</td>
                  <td className="pr-3 text-slate-600">{policy.gate}</td>
                  <td className="text-slate-600">{policy.requiredRefs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </details>
  );
}

function DraftReply({ scenario }: TicketWorkbenchProps) {
  if (!scenario.drafts) {
    return (
      <section className="mt-5 rounded-md border border-meter-line bg-[#f8fafc] p-4">
        <h3 className="text-sm font-semibold uppercase text-slate-500">Customer reply</h3>
        <p className="mt-3 text-sm leading-6 text-slate-600">No draft yet</p>
      </section>
    );
  }

  return (
    <section className="mt-5 rounded-md border border-meter-line bg-[#f8fafc] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase text-slate-500">Customer reply</h3>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-meter-blue">
          Draft only - not sent
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{scenario.drafts.customerReply}</p>
    </section>
  );
}

function approvalToneClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "approved") {
    return {
      panel: "border-meter-mint bg-[#f0fdf8]",
      label: "text-meter-mint",
    };
  }
  if (normalized === "rejected") {
    return {
      panel: "border-[#f2b8b8] bg-[#fff5f5]",
      label: "text-[#991b1b]",
    };
  }
  return {
    panel: "border-meter-amber bg-[#fffaf0]",
    label: "text-meter-amber",
  };
}
