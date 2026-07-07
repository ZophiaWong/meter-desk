import Link from "next/link";

import type { WorkbenchScenario } from "@/lib/meterdesk-view";

type TicketRailProps = {
  tickets: WorkbenchScenario["tickets"];
};

export function TicketRail({ tickets }: TicketRailProps) {
  return (
    <aside className="rounded-md border border-meter-line bg-white p-4 xl:sticky xl:top-6 xl:self-start">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Tickets</h2>
        <span className="rounded-full bg-[#e9f2fb] px-2.5 py-1 text-xs font-medium text-meter-blue">
          M3 API
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
        {tickets.map((ticket) => (
          <Link
            className={`block rounded-md border p-3 ${
              ticket.isActive
                ? "border-meter-blue bg-[#f7fbff]"
                : "border-meter-line bg-[#f8fafc] text-slate-500"
            }`}
            href={ticket.href}
            key={ticket.id}
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-sm font-semibold">{ticket.title}</h3>
              <span className="shrink-0 text-xs font-medium">{ticket.id}</span>
            </div>
            <p className="mt-2 text-sm">{ticket.customer}</p>
            <p className="mt-3 text-xs font-medium uppercase text-slate-500">{ticket.status}</p>
            <p className="mt-2 text-xs leading-5 text-slate-500">{ticket.summary}</p>
          </Link>
        ))}
      </div>
    </aside>
  );
}
