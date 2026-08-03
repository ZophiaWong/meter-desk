import {
  approveRequestAction,
  rejectRequestAction,
  startAgentRunAction,
} from "@/lib/meterdesk-actions";
import {
  AGENT_RUN_PERMISSION_EXPLANATION,
  APPROVAL_PERMISSION_EXPLANATION,
  canDecideApproval,
  canStartAgentRun,
  type DemoPrincipal,
} from "@/lib/demo-auth";
import type { WorkbenchScenario } from "@/lib/meterdesk-view";

type SafetyRailProps = {
  currentPrincipal: DemoPrincipal;
  scenario: WorkbenchScenario;
};

export function SafetyRail({ currentPrincipal, scenario }: SafetyRailProps) {
  return (
    <section
      aria-labelledby="safety-rail-heading"
      className="rounded-md border border-meter-line bg-white p-5 xl:sticky xl:top-24 xl:self-start"
      role="region"
    >
      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">Governance</p>
        <h2 id="safety-rail-heading" className="mt-2 text-lg font-semibold">
          Safety rail
        </h2>
      </div>
      <SafetySummaryCard currentPrincipal={currentPrincipal} scenario={scenario} />
      <RunStateCard currentPrincipal={currentPrincipal} scenario={scenario} />
      <ComplianceCard scenario={scenario} />
      <MutationResultList scenario={scenario} />
      <DraftReply scenario={scenario} />
    </section>
  );
}

function ComplianceCard({ scenario }: Pick<SafetyRailProps, "scenario">) {
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

function SafetySummaryCard({ currentPrincipal, scenario }: SafetyRailProps) {
  if (!scenario.approval) {
    return (
      <section
        aria-label="Safety summary"
        className="mt-4 rounded-md border border-meter-line bg-[#fbfcfe] p-4"
        role="region"
      >
        <p className="text-xs font-semibold uppercase text-slate-500">Safety summary</p>
        <h3 id="safety-summary-heading" className="mt-2 text-base font-semibold">
          No approval request
        </h3>
        <div className="mt-3 grid gap-2 text-xs font-semibold text-slate-600">
          <span>No approval required yet</span>
          <span>No mock mutation executed</span>
          <span>{scenario.drafts ? "Draft only" : "No draft"}</span>
        </div>
      </section>
    );
  }
  const isPending = scenario.approval.status.toLowerCase() === "pending";
  const canDecide = canDecideApproval(currentPrincipal);
  const tone = approvalToneClass(scenario.approval.status);
  const hasMutation = scenario.mutations.length > 0;

  return (
    <section
      aria-label="Safety summary"
      className={`mt-4 rounded-md border p-4 ${tone.panel}`}
      role="region"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={`text-xs font-semibold uppercase ${tone.label}`}>Safety summary</p>
          <h3 id="safety-summary-heading" className="mt-2 text-base font-semibold">
            {scenario.approval.status === "Pending"
              ? "Pending approval"
              : `${scenario.approval.status} approval`}
          </h3>
        </div>
        <span className="text-lg font-semibold">{scenario.approval.amount}</span>
      </div>
      <div className="mt-3 grid gap-2 text-xs font-semibold text-slate-700">
        <span>
          {scenario.approval.status === "Pending"
            ? "Approval gate pending"
            : `${scenario.approval.status} gate`}
        </span>
        <span>{hasMutation ? "Mock mutation executed" : "Mutation blocked"}</span>
        <span>{scenario.drafts ? "Draft only" : "No draft"}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{scenario.approval.reason}</p>
      <p className={`mt-3 text-sm font-medium ${tone.label}`}>{scenario.approval.blocker}</p>
      <p className="mt-2 text-xs text-slate-500">Policy: {scenario.approval.policyCitation}</p>
      {!isPending && scenario.approval.decisionActorSummary ? (
        <p className="mt-3 text-xs font-semibold text-slate-700">
          Decided by {scenario.approval.decisionActorSummary}
        </p>
      ) : null}
      <div className="mt-4 grid grid-cols-2 gap-2">
        <form action={approveRequestAction}>
          <input name="approvalId" type="hidden" value={scenario.approval.id} />
          <input name="ticketId" type="hidden" value={scenario.ticket.id} />
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
          <input name="approvalId" type="hidden" value={scenario.approval.id} />
          <input name="ticketId" type="hidden" value={scenario.ticket.id} />
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
    </section>
  );
}

function RunStateCard({ currentPrincipal, scenario }: SafetyRailProps) {
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
            className="h-10 rounded-md bg-meter-blue px-4 text-sm font-semibold text-white disabled:cursor-not-allowed"
            disabled={!canStartAgentRun(currentPrincipal)}
            title={
              !canStartAgentRun(currentPrincipal) ? AGENT_RUN_PERMISSION_EXPLANATION : undefined
            }
            type="submit"
          >
            Run investigation
          </button>
        </form>
      ) : null}
    </section>
  );
}

function MutationResultList({ scenario }: Pick<SafetyRailProps, "scenario">) {
  if (scenario.mutations.length === 0) {
    return (
      <section
        aria-label="Mock mutation"
        className="mt-4 rounded-md border border-meter-line bg-[#fbfcfe] p-4"
        role="region"
      >
        <h3 className="text-sm font-semibold uppercase text-slate-500">Mock mutation</h3>
        <p className="mt-3 text-sm leading-6 text-slate-600">No mock mutation executed</p>
      </section>
    );
  }
  return (
    <section
      aria-label="Mock mutation"
      className="mt-4 rounded-md border border-meter-mint bg-[#f0fdf8] p-4"
      role="region"
    >
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

function DraftReply({ scenario }: Pick<SafetyRailProps, "scenario">) {
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
