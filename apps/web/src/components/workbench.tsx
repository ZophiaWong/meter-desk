import type { DemoPrincipal } from "@/lib/demo-auth";
import type { WorkbenchScenario } from "@/lib/meterdesk-view";

import { BillingEvidence } from "./billing-evidence";
import { DecisionOverview } from "./decision-graph";
import { ProofAudit } from "./proof-audit";
import { SafetyRail } from "./safety-rail";
import { TicketRail } from "./ticket-rail";

type TicketWorkbenchProps = {
  currentPrincipal: DemoPrincipal;
  scenario: WorkbenchScenario;
};

export function TicketWorkbench({ currentPrincipal, scenario }: TicketWorkbenchProps) {
  return (
    <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)_340px] xl:items-start">
      <TicketRail tickets={scenario.tickets} />

      <section className="min-w-0 space-y-5">
        <TicketHeader scenario={scenario} />
        <GoldenPathStrip />
        <DecisionOverview
          graph={scenario.decisionGraph}
          summary={scenario.decisionSummary}
        />
        <WorkflowTimeline scenario={scenario} />
      </section>

      <SafetyRail currentPrincipal={currentPrincipal} scenario={scenario} />

      <section className="min-w-0 space-y-5 xl:col-start-2">
        <BillingEvidence evidence={scenario.evidence} />
        <InternalResolution scenario={scenario} />
        <ProofAudit scenario={scenario} />
      </section>
    </div>
  );
}

function WorkflowTimeline({ scenario }: Pick<TicketWorkbenchProps, "scenario">) {
  if (!scenario.workflow) {
    return null;
  }
  return (
    <section
      aria-label="Workflow state timeline"
      className="rounded-md border border-meter-line bg-white p-5"
      role="region"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Case workflow</p>
          <h2 className="mt-2 text-lg font-semibold">
            Cycle {scenario.workflow.cycleNumber} - {scenario.workflow.status}
          </h2>
        </div>
        <span className="rounded-full bg-[#eef5fb] px-2.5 py-1 text-xs font-semibold text-meter-blue">
          v{scenario.workflow.version}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600">
        {scenario.workflow.reason ?? scenario.workflow.reasonCode}
      </p>
      <ol className="mt-4 space-y-3 border-l border-meter-line pl-4">
        {(scenario.workflowTransitions ?? []).map((transition) => (
          <li className="relative text-sm" key={transition.id}>
            <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-meter-blue" />
            <p className="font-semibold text-slate-800">
              {transition.fromStatus ? `${transition.fromStatus} -> ` : ""}
              {transition.toStatus}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {transition.reasonDetail ?? transition.reasonCode}
            </p>
            <p className="mt-1 text-[11px] text-slate-400">
              {transition.createdAt} - {transition.actor ?? "System"} - {transition.requestId}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function GoldenPathStrip() {
  const steps = ["Evidence", "Policy", "Decision", "Approval", "Mutation"];

  return (
    <section
      aria-label="Golden path"
      className="rounded-md border border-meter-line bg-white px-4 py-3"
      role="region"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Golden path</p>
          <p className="mt-1 text-sm font-semibold text-meter-ink">Duplicate Charge walkthrough</p>
        </div>
        <ol className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-600">
          {steps.map((step, index) => (
            <li className="flex items-center gap-2" key={step}>
              {index > 0 ? <span className="text-slate-300">/</span> : null}
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function TicketHeader({ scenario }: Pick<TicketWorkbenchProps, "scenario">) {
  return (
    <section className="rounded-md border border-meter-line bg-white p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium text-meter-blue">{scenario.ticket.id}</p>
          <h1 className="mt-2 text-3xl font-semibold leading-tight">{scenario.ticket.title}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
            {scenario.ticket.summary}
          </p>
        </div>
        <div className="rounded-md border border-meter-line bg-[#fbfcfe] px-4 py-3 text-sm">
          <p className="font-semibold">{scenario.ticket.customer}</p>
          <p className="mt-1 text-slate-500">{scenario.ticket.severity}</p>
          <p className="mt-1 text-slate-500">Opened {scenario.ticket.openedAt}</p>
        </div>
      </div>
    </section>
  );
}

function InternalResolution({ scenario }: Pick<TicketWorkbenchProps, "scenario">) {
  return (
    <section className="rounded-md border border-meter-line bg-white p-5">
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
  );
}
