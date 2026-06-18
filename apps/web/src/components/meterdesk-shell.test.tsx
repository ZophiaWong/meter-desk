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
    outcome: "Seeded M5 baseline: duplicate captured charge confirmed.",
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
  run: null,
  traces: [],
  approval: null,
  mutations: [],
  drafts: null,
};

describe("MeterDeskShell", () => {
  it("renders M3 API-backed workbench data and empty run state", () => {
    render(<MeterDeskShell scenario={scenario} status={reachableStatus} />);

    expect(screen.getByRole("link", { name: "Ticket Workbench" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Approval Queue" })).toHaveAttribute(
      "href",
      "/approvals",
    );
    expect(screen.getByRole("link", { name: "Eval Lab" })).toHaveAttribute("href", "/eval-lab");
    expect(screen.getByText("API reachable")).toBeInTheDocument();
    expect(screen.getByText("Postgres reachable")).toBeInTheDocument();
    expect(screen.getByText("M3 API")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run investigation" })).toBeEnabled();
    expect(screen.getByText("No agent run yet")).toBeInTheDocument();
    expect(screen.getByText("No mock mutation executed")).toBeInTheDocument();

    const evidence = screen.getByRole("region", { name: "Billing evidence" });
    expect(within(evidence).getByText("Northstar Compute")).toBeInTheDocument();
    expect(within(evidence).getByText("INV-2026-0418")).toBeInTheDocument();
    expect(within(evidence).getByText("ch_2026_0418_A")).toBeInTheDocument();
    expect(within(evidence).getByText("ch_2026_0418_B")).toBeInTheDocument();
    expect(within(evidence).getByText("REFUND-DUP-001 v2026.02")).toBeInTheDocument();
  });

  it("renders draft-only output and active approval controls after a run", () => {
    render(
      <MeterDeskShell
        scenario={{
          ...scenario,
          run: {
            id: "RUN-2042",
            status: "Completed",
            model: "seeded-demo",
            promptVersion: "m3-duplicate-charge-v1",
            errorState: null,
          },
          traces: [
            {
              id: "trace-001",
              category: "approval.create_request",
              risk: "Medium",
              label: "Created approval request",
              output: "Approval request APR-2042 is pending.",
              evidence: "Evidence: invoice INV-2026-0418, charge ch_2026_0418_B",
            },
          ],
          approval: {
            id: "APR-2042",
            title: "Original refund pending approval",
            ticketId: "TCK-1042",
            amount: "$1,248.00",
            status: "Pending",
            reason: "Refund the second captured charge ch_2026_0418_B to the original payment method.",
            blocker: "Mutation blocked until human approval",
            policyCitation: "REFUND-DUP-001 v2026.02",
          },
          drafts: {
            internalResolution: "Confirmed duplicate payment on INV-2026-0418.",
            customerReply: "We are sending the duplicate charge for approval.",
          },
        }}
        status={reachableStatus}
      />,
    );

    expect(screen.getByText("RUN-2042")).toBeInTheDocument();
    expect(screen.getByText("seeded-demo")).toBeInTheDocument();
    expect(screen.getByText("Prompt: m3-duplicate-charge-v1")).toBeInTheDocument();
    expect(screen.getByText("Confirmed duplicate payment on INV-2026-0418.")).toBeInTheDocument();
    expect(screen.getByText("Draft only - not sent")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
    expect(screen.getByText("No mock mutation executed")).toBeInTheDocument();
  });

  it("renders failed run and approved mutation states for the demo path", () => {
    const failedScenario = {
      ...scenario,
      run: {
        id: "RUN-failed",
        status: "Failed",
        model: "live-model",
        promptVersion: "m3-duplicate-charge-v1",
        errorState: "Provider failed after retry: invalid structured output",
      },
    };

    const approvedScenario = {
      ...scenario,
      run: {
        id: "RUN-2042",
        status: "Completed",
        model: "seeded-demo",
        promptVersion: "m3-duplicate-charge-v1",
        errorState: null,
      },
      approval: {
        id: "APR-2042",
        title: "Original refund pending approval",
        ticketId: "TCK-1042",
        amount: "$1,248.00",
        status: "Approved",
        reason: "Refund the second captured charge ch_2026_0418_B to the original payment method.",
        blocker: "Approved; mock mutation executed",
        policyCitation: "REFUND-DUP-001 v2026.02",
      },
      mutations: [
        {
          id: "MM-2042",
          amount: "$1,248.00",
          status: "Mock executed",
          reason: "Approved original refund for duplicate captured charge.",
          executedAt: "Jun 5, 2026 12:10 UTC",
        },
      ],
    };

    const { rerender } = render(
      <MeterDeskShell scenario={failedScenario} status={reachableStatus} />,
    );

    expect(screen.getByText("Provider failed after retry: invalid structured output")).toBeInTheDocument();
    expect(screen.getByText("No approval request")).toBeInTheDocument();

    rerender(<MeterDeskShell scenario={approvedScenario} status={reachableStatus} />);

    expect(screen.getByText("MM-2042")).toBeInTheDocument();
    expect(screen.getByText("Approved; mock mutation executed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
  });

  it("shows an explicit backend error instead of falling back to static data", () => {
    render(<MeterDeskShell dataError="FastAPI domain data unavailable" status={reachableStatus} />);

    expect(screen.getByRole("heading", { name: "MeterDesk data unavailable" })).toBeInTheDocument();
    expect(screen.getByText("FastAPI domain data unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Duplicate charge investigation")).not.toBeInTheDocument();
  });
});
