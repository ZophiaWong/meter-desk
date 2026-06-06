import type { ServiceStatus, SystemStatus } from "@/lib/status";

const navItems = ["Ticket Workbench", "Approval Queue", "Eval Lab"];

type MeterDeskShellProps = {
  status: SystemStatus;
};

export function MeterDeskShell({ status }: MeterDeskShellProps) {
  return (
    <main className="min-h-screen bg-[#f7f8fb] text-meter-ink">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8">
        <header className="flex flex-col gap-6 border-b border-meter-line pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.12em] text-meter-blue">
              Governed billing support
            </p>
            <h1 className="mt-3 text-4xl font-semibold leading-tight md:text-5xl">MeterDesk</h1>
          </div>

          <nav aria-label="Primary" className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <button
                aria-disabled="true"
                className="h-10 rounded-md border border-meter-line bg-white px-4 text-sm font-medium text-slate-500"
                disabled
                key={item}
                type="button"
              >
                {item}
              </button>
            ))}
          </nav>
        </header>

        <div className="grid flex-1 gap-6 py-8 lg:grid-cols-[1.35fr_0.65fr]">
          <section className="p-1">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="text-xl font-semibold">System status</h2>
              </div>
              <p className="text-sm text-slate-500">
                {status.checkedAt ? formatCheckedAt(status.checkedAt) : "Not checked"}
              </p>
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-2">
              <StatusPanel status={status.api} />
              <StatusPanel status={status.database} />
            </div>
          </section>

          <aside className="rounded-lg border border-meter-line bg-[#fbfcfe] p-6">
            <h2 className="text-base font-semibold">Stack</h2>
            <dl className="mt-6 space-y-5 text-sm">
              <div className="flex items-center justify-between gap-4">
                <dt className="text-slate-500">Frontend</dt>
                <dd className="font-medium">Next.js</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-slate-500">Backend</dt>
                <dd className="font-medium">FastAPI</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-slate-500">Database</dt>
                <dd className="font-medium">Postgres</dd>
              </div>
            </dl>
          </aside>
        </div>
      </section>
    </main>
  );
}

function StatusPanel({ status }: { status: ServiceStatus }) {
  const isOk = status.state === "ok";
  const indicatorClass = isOk ? "bg-meter-mint" : "bg-meter-amber";
  const stateLabel = isOk ? "Reachable" : "Unavailable";

  return (
    <div className="min-h-36 rounded-md border border-meter-line bg-[#fdfefe] p-5">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-sm font-semibold uppercase tracking-[0.1em] text-slate-500">
          {status.label}
        </h3>
        <span className="inline-flex items-center gap-2 text-sm font-medium">
          <span className={`h-2.5 w-2.5 rounded-full ${indicatorClass}`} />
          {stateLabel}
        </span>
      </div>
      <p className="mt-8 text-lg font-semibold">{status.detail}</p>
    </div>
  );
}

function formatCheckedAt(value: string) {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}
