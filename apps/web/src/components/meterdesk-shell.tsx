import { duplicateChargeScenario } from "@/data/m1-scenario";
import type { SystemStatus } from "@/lib/status";
import Link from "next/link";

import { TicketWorkbench } from "./workbench";

type MeterDeskShellProps = {
  status: SystemStatus;
};

export function MeterDeskShell({ status }: MeterDeskShellProps) {
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
            {duplicateChargeScenario.nav.map((item) => (
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
        <TicketWorkbench scenario={duplicateChargeScenario} />
      </section>
    </main>
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
