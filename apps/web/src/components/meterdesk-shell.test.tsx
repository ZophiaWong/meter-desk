import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MeterDeskShell } from "./meterdesk-shell";
import type { WorkbenchScenario } from "@/lib/meterdesk-view";

const checkedAt = "2026-06-05T12:00:00.000Z";
const reachableStatus = {
  api: { label: "API", state: "ok" as const, detail: "FastAPI reachable" },
  database: { label: "Postgres", state: "ok" as const, detail: "Database reachable" },
  checkedAt,
};

const scenario: WorkbenchScenario = {
  nav: [
    { label: "Ticket Workbench", href: "/" },
    { label: "Approval Queue", href: "/approvals" },
    { label: "Eval Lab", href: "/eval-lab" },
  ],
  tickets: [
    {
      id: "TCK-1042",
      title: "Same invoice charged twice",
      customer: "Northstar Compute",
      status: "Ready for approval",
      summary: "Two captured charges are attached to INV-2026-0418.",
      isActive: true,
    },
    {
      id: "TCK-1098",
      title: "Usage Spike",
      customer: "Atlas Labs",
      status: "Seeded support scenario",
      summary: "May token usage increased after a batch import job.",
      isActive: false,
    },
  ],
  ticket: {
    id: "TCK-1042",
    title: "Duplicate charge investigation",
    customer: "Northstar Compute",
    severity: "Billing dispute",
    openedAt: "Jun 5, 2026",
    summary: "Customer reports that April usage was paid once but appears twice.",
    outcome: "Agent classified this as a confirmed duplicate charge.",
  },
  evidence: {
    account: {
      name: "Northstar Compute",
      plan: "Scale API Platform",
      owner: "billing@northstar.example",
      status: "Active account, no collections hold",
    },
    invoice: {
      id: "INV-2026-0418",
      period: "Apr 1-30, 2026",
      total: "$1,248.00",
      status: "Paid",
    },
    charges: [
      {
        id: "ch_2026_0418_A",
        status: "Captured",
        amount: "$1,248.00",
        capturedAt: "May 1, 2026 09:14 UTC",
        processorState: "Linked to INV-2026-0418",
      },
      {
        id: "ch_2026_0418_B",
        status: "Captured",
        amount: "$1,248.00",
        capturedAt: "May 1, 2026 09:16 UTC",
        processorState: "Linked to INV-2026-0418",
      },
    ],
    credits: {
      label: "Credit balance unchanged",
      detail: "No prior adjustment or credit consumed against this duplicate capture.",
    },
    usage: {
      label: "No usage spike detected",
      detail: "April metered usage matches the paid invoice.",
    },
    policy: {
      id: "REFUND-DUP-001 v2026.02",
      title: "Duplicate captured payment",
      reason: "Same invoice, same amount, and two captured charges qualify.",
    },
  },
  traces: [
    {
      id: "trace-001",
      category: "read.billing_evidence",
      risk: "Low",
      label: "Collected invoice and charge evidence",
      output: "Found one paid invoice with two captured charges.",
      evidence: "Evidence: invoice INV-2026-0418, charges ch_2026_0418_A/ch_2026_0418_B",
    },
  ],
  approval: {
    id: "APR-2042",
    title: "Original refund pending approval",
    ticketId: "TCK-1042",
    amount: "$1,248.00",
    status: "Pending",
    reason: "Refund the second captured charge ch_2026_0418_B to the original payment method.",
    blocker: "Read-only in M2 - mutation blocked until M3 approval execution",
    policyCitation: "REFUND-DUP-001 v2026.02",
  },
  drafts: {
    internalResolution: "Confirmed duplicate payment on INV-2026-0418.",
    customerReply: "If approved, we will refund the duplicate charge.",
  },
};

describe("MeterDeskShell", () => {
  it("renders M2 API-backed workbench data and service status", () => {
    render(<MeterDeskShell scenario={scenario} status={reachableStatus} />);

    expect(screen.getByRole("link", { name: "Ticket Workbench" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Approval Queue" })).toHaveAttribute(
      "href",
      "/approvals",
    );
    expect(screen.getByRole("link", { name: "Eval Lab" })).toHaveAttribute("href", "/eval-lab");
    expect(screen.getByText("API reachable")).toBeInTheDocument();
    expect(screen.getByText("Postgres reachable")).toBeInTheDocument();
    expect(screen.getByText("M2 API")).toBeInTheDocument();

    const evidence = screen.getByRole("region", { name: "Billing evidence" });
    expect(within(evidence).getByText("Northstar Compute")).toBeInTheDocument();
    expect(within(evidence).getByText("INV-2026-0418")).toBeInTheDocument();
    expect(within(evidence).getByText("ch_2026_0418_A")).toBeInTheDocument();
    expect(within(evidence).getByText("ch_2026_0418_B")).toBeInTheDocument();
    expect(within(evidence).getByText("REFUND-DUP-001 v2026.02")).toBeInTheDocument();
  });

  it("shows an explicit backend error instead of falling back to static data", () => {
    render(<MeterDeskShell dataError="FastAPI domain data unavailable" status={reachableStatus} />);

    expect(screen.getByRole("heading", { name: "MeterDesk data unavailable" })).toBeInTheDocument();
    expect(screen.getByText("FastAPI domain data unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Duplicate charge investigation")).not.toBeInTheDocument();
  });
});
