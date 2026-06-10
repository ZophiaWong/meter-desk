import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ApprovalsPage from "./approvals/page";
import EvalLabPage from "./eval-lab/page";

const tickets = [
  {
    id: "TCK-1042",
    title: "Same invoice charged twice",
    customer: "Northstar Compute",
    status: "Ready for approval",
    summary: "Two captured charges are attached to INV-2026-0418.",
    scenario: "duplicate_charge",
    is_active: true,
  },
];

const approvals = [
  {
    id: "APR-2042",
    ticket_id: "TCK-1042",
    title: "Original refund pending approval",
    status: "pending",
    action_type: "original_refund",
    agent_run_id: "RUN-2042",
    amount: { amount_cents: 124800, currency: "USD", display: "$1,248.00" },
    reason: "Refund the second captured charge ch_2026_0418_B to the original payment method.",
    policy_citation: "REFUND-DUP-001 v2026.02",
    blocker: "Mutation blocked until human approval",
    evidence_refs: ["invoice INV-2026-0418", "charge ch_2026_0418_B"],
    action_metadata: {
      action_type: "original_refund",
      invoice_id: "INV-2026-0418",
      target_charge_id: "ch_2026_0418_B",
    },
    decided_at: null,
    decision: null,
    decided_by: null,
    decision_note: null,
  },
];

const evalCases = [
  "eval-duplicate-charge-001",
  "eval-duplicate-charge-002",
  "eval-duplicate-charge-003",
  "eval-usage-spike-001",
  "eval-usage-spike-002",
  "eval-usage-spike-003",
  "eval-credit-refund-001",
  "eval-credit-refund-002",
  "eval-credit-refund-003",
].map((id) => ({
  id,
  scenario: id.includes("usage-spike")
    ? "usage_spike"
    : id.includes("credit-refund")
      ? "credit_refund_dispute"
      : "duplicate_charge",
  title: id,
  description: `${id} description`,
  expected_outcome: "expected outcome",
  required_evidence: ["invoice", "policy"],
  policy_refs: ["REFUND-DUP-001 v2026.02"],
  expected_approval_routing: "approval expectation",
}));

const evalResults: unknown[] = [];

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockApi(payloads: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const rawUrl = input instanceof Request ? input.url : input.toString();
      const url = new URL(rawUrl);
      const payload = payloads[url.pathname];

      if (payload === undefined) {
        return new Response("Not found", { status: 404 });
      }

      return new Response(JSON.stringify(payload), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      });
    }),
  );
}

describe("M3 API-backed routes", () => {
  it("renders pending approval queue entries from FastAPI resources", async () => {
    mockApi({
      "/approvals": approvals,
      "/tickets": tickets,
    });

    render(await ApprovalsPage());

    expect(screen.getByRole("heading", { name: "Approval Queue" })).toBeInTheDocument();
    expect(screen.getByText("Original refund pending approval")).toBeInTheDocument();
    expect(screen.getByText("TCK-1042")).toBeInTheDocument();
    expect(screen.getByText("Northstar Compute")).toBeInTheDocument();
    expect(screen.getByText("$1,248.00")).toBeInTheDocument();
    expect(screen.getByText("Mutation blocked until human approval")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
  });

  it("renders all nine eval cases with no preview result before M4 runs", async () => {
    mockApi({
      "/eval-cases": evalCases,
      "/eval-results": evalResults,
    });

    render(await EvalLabPage());

    expect(screen.getByRole("heading", { name: "Eval Lab" })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(9);
    expect(screen.getAllByText("No run yet")).toHaveLength(9);
  });
});
