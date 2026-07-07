import type { WorkbenchScenario } from "@/lib/meterdesk-view";

import { BillingEvidence } from "./billing-evidence";
import { DecisionOverview } from "./decision-graph";
import { SafetyRail } from "./safety-rail";
import { TicketRail } from "./ticket-rail";

type TicketWorkbenchProps = {
  scenario: WorkbenchScenario;
};

export function TicketWorkbench({ scenario }: TicketWorkbenchProps) {
  return (
    <div className="grid gap-5 py-6 xl:grid-cols-[240px_minmax(0,1fr)]">
      <TicketRail tickets={scenario.tickets} />

      <section className="min-w-0 space-y-5">
        <TicketHeader scenario={scenario} />

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="min-w-0 space-y-5">
            <DecisionOverview
              graph={scenario.decisionGraph}
              summary={scenario.decisionSummary}
            />
            <BillingEvidence evidence={scenario.evidence} />
            <InternalResolution scenario={scenario} />
          </div>

          <SafetyRail scenario={scenario} />
        </div>
      </section>
    </div>
  );
}

function TicketHeader({ scenario }: TicketWorkbenchProps) {
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

function InternalResolution({ scenario }: TicketWorkbenchProps) {
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
