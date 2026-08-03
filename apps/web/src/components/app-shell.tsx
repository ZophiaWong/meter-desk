import Link from "next/link";
import type { ReactNode } from "react";

import type { DemoPrincipal } from "@/lib/demo-auth";
import { formatDemoRole } from "@/lib/demo-auth";
import { logoutAction } from "@/lib/auth-actions";
import { NAV_ITEMS, type ServiceSurface } from "@/lib/meterdesk-view";
import type { SystemStatus } from "@/lib/status";

type AppShellProps = {
  activeSurface: ServiceSurface["label"];
  children: ReactNode;
  currentPrincipal: DemoPrincipal;
  returnTo?: string;
  status: SystemStatus;
};

export function AppShell({
  activeSurface,
  children,
  currentPrincipal,
  returnTo = "/",
  status,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-[#f7f8fb] text-meter-ink">
      <header className="sticky top-0 z-30 border-b border-meter-line bg-white/95 backdrop-blur">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-3 px-5 py-3 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <Link className="text-lg font-semibold tracking-tight text-meter-ink" href="/">
              MeterDesk
            </Link>
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-meter-blue">
              Governed billing support
            </span>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <nav aria-label="Primary" className="flex flex-wrap gap-1">
              {NAV_ITEMS.map((item) => {
                const isActive = item.label === activeSurface;
                return (
                  <Link
                    aria-current={isActive ? "page" : undefined}
                    className={`inline-flex h-9 items-center rounded-md border px-3 text-sm font-semibold ${
                      isActive
                        ? "border-meter-blue bg-[#e9f2fb] text-meter-blue"
                        : "border-transparent text-slate-600 hover:border-meter-line hover:bg-[#fbfcfe]"
                    }`}
                    href={item.href}
                    key={item.href}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <div className="flex flex-wrap items-center gap-2 border-l border-meter-line pl-3 text-xs">
              <div>
                <p className="font-semibold text-meter-ink">{currentPrincipal.display_name}</p>
                <p className="text-slate-500">{formatDemoRole(currentPrincipal.role)}</p>
              </div>
              <Link
                className="font-semibold text-meter-blue"
                href={`/login?mode=switch&returnTo=${encodeURIComponent(returnTo)}`}
              >
                Switch identity
              </Link>
              <form action={logoutAction}>
                <button className="font-semibold text-slate-600" type="submit">
                  Log out
                </button>
              </form>
            </div>
            <StatusStrip status={status} />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1440px] px-5 py-5 lg:px-8">{children}</main>
    </div>
  );
}

function StatusStrip({ status }: { status: SystemStatus }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
      <ServiceBadge label="API" state={status.api.state} />
      <ServiceBadge label="Postgres" state={status.database.state} />
      <span className="hidden xl:inline">
        {status.checkedAt ? `Checked ${formatCheckedAt(status.checkedAt)}` : "Not checked"}
      </span>
    </div>
  );
}

function ServiceBadge({ label, state }: { label: string; state: "ok" | "down" }) {
  const isOk = state === "ok";

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-meter-line bg-[#fbfcfe] px-2.5 py-1 font-medium">
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
