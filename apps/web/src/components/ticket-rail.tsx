import Link from "next/link";

import type { WorkbenchScenario } from "@/lib/meterdesk-view";

type TicketRailProps = {
  tickets: WorkbenchScenario["tickets"];
};

export function TicketRail({ tickets }: TicketRailProps) {
  const groupedTickets = groupTickets(tickets);

  return (
    <aside
      aria-labelledby="ticket-queue-heading"
      className="rounded-md border border-meter-line bg-white p-4 xl:sticky xl:top-24 xl:self-start"
      role="region"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 id="ticket-queue-heading" className="text-sm font-semibold uppercase text-slate-500">
          Ticket queue
        </h2>
        <span className="rounded-full bg-[#e9f2fb] px-2.5 py-1 text-xs font-medium text-meter-blue">
          {tickets.length} cases
        </span>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
        {groupedTickets.map(([scenario, scenarioTickets]) => (
          <section key={scenario}>
            <h3 className="text-xs font-semibold uppercase text-slate-500">{scenario}</h3>
            <div className="mt-2 grid gap-2">
              {scenarioTickets.map((ticket) => (
                <Link
                  aria-current={ticket.isActive ? "page" : undefined}
                  className={`block rounded-md border p-3 transition ${
                    ticket.isActive
                      ? "border-meter-blue bg-[#f7fbff]"
                      : "border-meter-line bg-[#f8fafc] text-slate-500 hover:border-meter-blue"
                  }`}
                  href={ticket.href}
                  key={ticket.id}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-meter-blue">{ticket.id}</p>
                      <h4 className="mt-1 text-sm font-semibold leading-snug">{ticket.title}</h4>
                    </div>
                    <span className="shrink-0 rounded-full bg-white px-2 py-1 text-[11px] font-semibold text-slate-600">
                      {ticketSignal(ticket.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm">{ticket.customer}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-500">{ticket.summary}</p>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </aside>
  );
}

function groupTickets(tickets: TicketRailProps["tickets"]) {
  const groups = new Map<string, TicketRailProps["tickets"]>();
  for (const ticket of tickets) {
    const existing = groups.get(ticket.scenario) ?? [];
    existing.push(ticket);
    groups.set(ticket.scenario, existing);
  }
  return Array.from(groups.entries());
}

function ticketSignal(status: string) {
  if (status.toLowerCase().includes("approval")) {
    return "Needs approval";
  }
  if (status.toLowerCase().includes("blocked")) {
    return "Blocked";
  }
  return "Ready";
}
