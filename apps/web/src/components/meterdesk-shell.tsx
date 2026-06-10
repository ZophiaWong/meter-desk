import type { SystemStatus } from "@/lib/status";
import { NAV_ITEMS, type WorkbenchScenario } from "@/lib/meterdesk-view";
import Link from "next/link";

import { TicketWorkbench } from "./workbench";

type MeterDeskShellProps = {
  dataError?: string;
  scenario?: WorkbenchScenario;
  status: SystemStatus;
};

export function MeterDeskShell({ dataError, scenario, status }: MeterDeskShellProps) {
  return (
    <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
      <section className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-5 py-6 lg:px-8">
        <header className="flex flex-col gap-5 border-b border-meter-line pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.12em] text-meter-blue">
              Governed billing support
            </p>
            <h1 className="mt-2 text-4xl font-semibold leading-tight">MeterDesk</h1>
          </div>

          <nav aria-label="Primary" className="flex flex-wrap gap-2">
            {NAV_ITEMS.map((item) => (
              <Link
                className="inline-flex h-10 items-center rounded-md border border-meter-line bg-white px-4 text-sm font-medium text-meter-ink hover:border-meter-blue"
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </header>

        <StatusStrip status={status} />
        {scenario ? <TicketWorkbench scenario={scenario} /> : <DataErrorPanel message={dataError} />}
      </section>
    </main>
  );
}

function DataErrorPanel({ message }: { message?: string }) {
  return (
    <section className="mt-6 rounded-md border border-meter-amber bg-[#fffaf0] p-5">
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

function StatusStrip({ status }: { status: SystemStatus }) {
  return (
    <div className="mt-4 flex flex-col gap-2 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap gap-2">
        <ServiceBadge label="API" state={status.api.state} />
        <ServiceBadge label="Postgres" state={status.database.state} />
      </div>
      <span>{status.checkedAt ? `Checked ${formatCheckedAt(status.checkedAt)}` : "Not checked"}</span>
    </div>
  );
}

function ServiceBadge({ label, state }: { label: string; state: "ok" | "down" }) {
  const isOk = state === "ok";

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-meter-line bg-white px-3 py-1 font-medium">
      <span className={`h-2 w-2 rounded-full ${isOk ? "bg-meter-mint" : "bg-meter-amber"}`} />
      {label} {isOk ? "reachable" : "unavailable"}
    </span>
  );
}

function formatCheckedAt(value: string) {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}
