import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MeterDeskShell } from "./meterdesk-shell";

const checkedAt = "2026-06-05T12:00:00.000Z";
const reachableStatus = {
  api: { label: "API", state: "ok" as const, detail: "FastAPI reachable" },
  database: { label: "Postgres", state: "ok" as const, detail: "Database reachable" },
  checkedAt,
};

describe("MeterDeskShell", () => {
  it("renders M1 navigation links and weak local service status", () => {
    render(<MeterDeskShell status={reachableStatus} />);

    expect(screen.getByRole("link", { name: "Ticket Workbench" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Approval Queue" })).toHaveAttribute(
      "href",
      "/approvals",
    );
    expect(screen.getByRole("link", { name: "Eval Lab" })).toHaveAttribute("href", "/eval-lab");
    expect(screen.getByText("API reachable")).toBeInTheDocument();
    expect(screen.getByText("Postgres reachable")).toBeInTheDocument();
  });

  it("renders the Duplicate Charge workbench with required billing evidence", () => {
    render(<MeterDeskShell status={reachableStatus} />);

    expect(screen.getByRole("heading", { name: "Duplicate charge investigation" })).toBeInTheDocument();
    expect(screen.getByText("Same invoice charged twice")).toBeInTheDocument();
    expect(screen.getByText("Usage Spike")).toBeInTheDocument();
    expect(screen.getByText("Credit/Refund Dispute")).toBeInTheDocument();

    const evidence = screen.getByRole("region", { name: "Billing evidence" });
    expect(within(evidence).getByText("Northstar Compute")).toBeInTheDocument();
    expect(within(evidence).getByText("INV-2026-0418")).toBeInTheDocument();
    expect(within(evidence).getByText("ch_2026_0418_A")).toBeInTheDocument();
    expect(within(evidence).getByText("ch_2026_0418_B")).toBeInTheDocument();
    expect(within(evidence).getByText("Credit balance unchanged")).toBeInTheDocument();
    expect(within(evidence).getByText("No usage spike detected")).toBeInTheDocument();
    expect(within(evidence).getByText("REFUND-DUP-001 v2026.02")).toBeInTheDocument();
  });

  it("shows traceable governance, pending approval, and draft-only customer text", () => {
    render(<MeterDeskShell status={reachableStatus} />);

    const governance = screen.getByRole("region", { name: "Governance and trace" });
    expect(within(governance).getByText("Original refund pending approval")).toBeInTheDocument();
    expect(within(governance).getByText("$1,248.00")).toBeInTheDocument();
    expect(within(governance).getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(within(governance).getByRole("button", { name: "Reject" })).toBeDisabled();
    expect(within(governance).queryByText("Mock mutation executed")).not.toBeInTheDocument();
    expect(within(governance).getByText("read.billing_evidence")).toBeInTheDocument();
    expect(within(governance).getByText("decision.refund_eligibility")).toBeInTheDocument();
    expect(within(governance).getByText("Evidence: invoice INV-2026-0418, charges A/B")).toBeInTheDocument();
    expect(within(governance).getByText("Draft only - not sent")).toBeInTheDocument();
    expect(
      within(governance).getByText(/If approved, we will refund the duplicate charge/),
    ).toBeInTheDocument();
  });
});
