import {
  approveRequestAction,
  rejectRequestAction,
  startAgentRunAction,
} from "@/lib/meterdesk-actions";
import type { WorkbenchScenario } from "@/lib/meterdesk-view";

import { TraceDiagnostics } from "./trace-diagnostics";

type SafetyRailProps = {
  scenario: WorkbenchScenario;
};

export function SafetyRail({ scenario }: SafetyRailProps) {
  return (
    <section
      aria-labelledby="safety-rail-heading"
      className="rounded-md border border-meter-line bg-white p-5 xl:sticky xl:top-6 xl:self-start"
      role="region"
    >
      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">Governance</p>
        <h2 id="safety-rail-heading" className="mt-2 text-lg font-semibold">
          Safety rail
        </h2>
      </div>
      <GovernanceRulesDrawer scenario={scenario} />
      <RunStateCard scenario={scenario} />
      <ComplianceCard scenario={scenario} />
      <ApprovalCard scenario={scenario} />
      <MutationResultList scenario={scenario} />
      <TraceDiagnostics traces={scenario.traces} />
      <DraftReply scenario={scenario} />
    </section>
  );
}

function ComplianceCard({ scenario }: SafetyRailProps) {
  if (!scenario.compliance) {
    return null;
  }

  const failed = scenario.compliance.status === "Failed";
  return (
    <section
      className={`mt-4 rounded-md border p-4 ${
        failed ? "border-[#f2b8b8] bg-[#fff5f5]" : "border-meter-line bg-[#fbfcfe]"
      }`}
    >
      <p className="text-xs font-semibold uppercase text-slate-500">Run compliance</p>
      <h3 className="mt-2 text-base font-semibold">Compliance: {scenario.compliance.status}</h3>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
        <p>{scenario.compliance.verifiedGovernedActionCount} governed actions verified</p>
        <p>{scenario.compliance.highRiskGateCount} high-risk gate</p>
      </div>
      {scenario.compliance.reasonCodes ? (
        <p className="mt-3 text-xs font-medium text-[#991b1b]">
          {scenario.compliance.reasonCodes}
        </p>
      ) : null}
    </section>
  );
}

function ApprovalCard({ scenario }: SafetyRailProps) {
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
          <input name="ticketId" type="hidden" value={scenario.ticket.id} />
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
          <input name="ticketId" type="hidden" value={scenario.ticket.id} />
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

function RunStateCard({ scenario }: SafetyRailProps) {
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
        <form action={startAgentRunAction} className="mt-4">
          <input name="ticketId" type="hidden" value={scenario.ticket.id} />
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

function MutationResultList({ scenario }: SafetyRailProps) {
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

function GovernanceRulesDrawer({ scenario }: SafetyRailProps) {
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
        {scenario.compliance ? (
          <div className="rounded-md border border-meter-line bg-white p-3 text-xs text-slate-600">
            <h3 className="font-semibold text-slate-800">Compliance diagnostics</h3>
            {scenario.compliance.reasonCodes ? (
              <p className="mt-2">Reason codes: {scenario.compliance.reasonCodes}</p>
            ) : null}
            {scenario.compliance.affectedTraceIds ? (
              <p className="mt-2">Affected traces: {scenario.compliance.affectedTraceIds}</p>
            ) : null}
            {scenario.compliance.missingRefs ? (
              <p className="mt-2">Missing refs: {scenario.compliance.missingRefs}</p>
            ) : null}
            {scenario.compliance.policyVersions ? (
              <p className="mt-2">Policy versions: {scenario.compliance.policyVersions}</p>
            ) : null}
          </div>
        ) : null}
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

function DraftReply({ scenario }: SafetyRailProps) {
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
