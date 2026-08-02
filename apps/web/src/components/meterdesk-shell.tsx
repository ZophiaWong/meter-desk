import type { DemoPrincipal } from "@/lib/demo-auth";
import type { SystemStatus } from "@/lib/status";
import type { WorkbenchScenario } from "@/lib/meterdesk-view";

import { AppShell } from "./app-shell";
import { TicketWorkbench } from "./workbench";

type MeterDeskShellProps = {
  currentPrincipal: DemoPrincipal;
  dataError?: string;
  scenario?: WorkbenchScenario;
  status: SystemStatus;
};

export function MeterDeskShell({ currentPrincipal, dataError, scenario, status }: MeterDeskShellProps) {
  return (
    <AppShell activeSurface="Ticket Workbench" currentPrincipal={currentPrincipal} status={status}>
      {scenario ? (
        <TicketWorkbench currentPrincipal={currentPrincipal} scenario={scenario} />
      ) : (
        <DataErrorPanel message={dataError} />
      )}
    </AppShell>
  );
}

function DataErrorPanel({ message }: { message?: string }) {
  return (
    <section className="rounded-md border border-meter-amber bg-[#fffaf0] p-5">
      <h2 className="text-xl font-semibold">MeterDesk data unavailable</h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
        {message ?? "FastAPI domain data unavailable"}
      </p>
      <p className="mt-3 text-sm font-medium text-meter-amber">
        M3 does not fall back to static demo data when backend resources are unavailable.
      </p>
    </section>
  );
}
