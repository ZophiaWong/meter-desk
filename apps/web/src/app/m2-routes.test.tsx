import "@testing-library/jest-dom/vitest";

import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const adminSession = {
  accessToken: "admin-session-token",
  principal: {
    subject: "demo-admin",
    display_name: "Demo Admin",
    role: "admin" as const,
  },
};

vi.mock("@/lib/session", () => ({
  handleProtectedApiError: vi.fn(),
  requireDemoSession: vi.fn(async () => adminSession),
}));

import ApprovalsPage from "./approvals/page";
import EvalLabPage from "./eval-lab/page";
import { handleProtectedApiError, requireDemoSession } from "@/lib/session";

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
    action_fingerprint:
      "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD",
    decided_at: null,
    decision: null,
    decision_actor: null,
    decision_request_id: null,
    decision_note: null,
  },
];

const terminalApprovals = [
  {
    ...approvals[0],
    id: "APR-2042-APPROVED",
    status: "approved",
    blocker: "Approved; mock mutation executed",
    decided_at: "2026-06-05T12:10:00Z",
    decision: "approved",
    decision_actor: {
      subject: "demo-approver",
      display_name: "Demo Approver",
      role: "approver",
      source: "demo_session",
    },
    decision_request_id: "req_approved_demo",
    decision_note: "Approved for demo.",
  },
  {
    ...approvals[0],
    id: "APR-2042-REJECTED",
    status: "rejected",
    blocker: "Rejected by human reviewer; no mock mutation executed",
    decided_at: "2026-06-05T12:11:00Z",
    decision: "rejected",
    decision_actor: {
      subject: "demo-approver",
      display_name: "Demo Approver",
      role: "approver",
      source: "demo_session",
    },
    decision_request_id: "req_rejected_demo",
    decision_note: "Rejected for demo.",
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
  fixture_ticket_id: id.startsWith("eval-duplicate-charge") ? `EVAL-${id}` : null,
}));

const evalResults = [
  {
    id: "EVAL-RESULT-001",
    case_id: "eval-duplicate-charge-001",
    agent_run_id: "RUN-EVAL-001",
    status: "passed",
    summary: "Deterministic eval checks passed.",
    dimension_scores: {
      outcome_correctness: "pass",
      required_evidence: "pass",
      policy_compliance: "pass",
      approval_routing: "pass",
      mutation_safety: "pass",
      tool_planning: "pass",
      governance_compliance: "pass",
      draft_safety: "pass",
      draft_quality: "not_run",
    },
    details: {
      failed_checks: [],
      missing_evidence: [],
      policy_refs_seen: ["REFUND-DUP-001 v2026.02"],
      trace_refs: [
        {
          id: "trace-eval-001",
          category: "read.billing_evidence",
          evidence_refs: ["invoice INV-EVAL-DUP-001"],
          policy_refs: ["REFUND-DUP-001 v2026.02"],
        },
      ],
      blocked_reason: null,
      compliance: {
        status: "passed",
        reason_codes: [],
        affected_trace_ids: [],
        missing_ref_categories: [],
        policy_versions_seen: {
          "read.billing_evidence": "1.0.0",
        },
        high_risk_gate_count: 1,
        verified_governed_action_count: 5,
      },
      judge_notes: ["Draft quality judge not configured."],
      model: "fake-eval-model",
      prompt_version: "m3-duplicate-charge-v1",
    },
  },
  {
    id: "EVAL-RESULT-004",
    case_id: "eval-usage-spike-001",
    agent_run_id: null,
    status: "blocked",
    summary: "Scenario runner is not implemented for this scenario",
    dimension_scores: {
      outcome_correctness: "blocked",
      required_evidence: "blocked",
      policy_compliance: "blocked",
      approval_routing: "blocked",
      mutation_safety: "blocked",
      tool_planning: "blocked",
      governance_compliance: "blocked",
      draft_safety: "blocked",
      draft_quality: "not_run",
    },
    details: {
      failed_checks: [],
      missing_evidence: ["invoice", "policy"],
      policy_refs_seen: [],
      trace_refs: [],
      blocked_reason: "Scenario runner is not implemented for this scenario",
      blocked_code: "scenario.runner_not_implemented",
      readiness_gaps: ["usage meter evidence model", "pricing evidence model"],
      recommended_next_scenario: "usage_spike",
      judge_notes: [],
    },
  },
];

const evalRegressionSummary = {
  baseline_run_id: "EVAL-RUN-BASELINE-M10",
  baseline_name: "M10 seeded canonical baseline",
  latest_run_id: null,
  latest_run_type: null,
  latest_run_completed_at: null,
  counts: {
    regressed: 0,
    improved: 0,
    unchanged: 0,
    incomparable: 0,
    coverage_gap: 0,
  },
  blocking_pass_rate: "0/0",
  cases: [],
};

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

function mockApi(payloads: Record<string, unknown>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      void init;
      const rawUrl = input instanceof Request ? input.url : input.toString();
      const url = new URL(rawUrl);
      const payload =
        payloads[url.pathname] ??
        (url.pathname === "/health" || url.pathname === "/health/db"
          ? { status: "ok" }
          : undefined);

      if (payload === undefined) {
        return new Response("Not found", { status: 404 });
      }

      if (payload instanceof Response) {
        return payload;
      }

      return new Response(JSON.stringify(payload), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      });
    });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("M3 API-backed routes", () => {
  it("renders pending approval queue entries from FastAPI resources", async () => {
    const fetchMock = mockApi({
      "/approvals": approvals,
      "/tickets": tickets,
    });

    render(await ApprovalsPage({}));

    expect(screen.getByRole("banner")).toHaveClass("sticky");
    expect(screen.getByRole("link", { name: "Ticket Workbench" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Approval Queue" })).toHaveAttribute(
      "href",
      "/approvals",
    );
    expect(screen.getByRole("link", { name: "Eval Lab" })).toHaveAttribute("href", "/eval-lab");
    expect(screen.getByText("API reachable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Approval Queue" })).toBeInTheDocument();
    expect(screen.getByText("Original refund pending approval")).toBeInTheDocument();
    expect(screen.getByText("TCK-1042")).toBeInTheDocument();
    expect(screen.getByText("Northstar Compute")).toBeInTheDocument();
    expect(screen.getByText("$1,248.00")).toBeInTheDocument();
    expect(screen.getByText("Mutation blocked until human approval")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
    expect(screen.getByText("Demo Admin")).toBeInTheDocument();
    const protectedCalls = fetchMock.mock.calls.filter(([input]) => {
      const url = new URL(input instanceof Request ? input.url : input.toString());
      return url.pathname === "/approvals" || url.pathname === "/tickets";
    });
    expect(protectedCalls).toHaveLength(2);
    for (const [, init] of protectedCalls) {
      expect(init).toMatchObject({
        headers: { Authorization: "Bearer admin-session-token" },
      });
    }
  });

  it("renders approved and rejected approval queue states", async () => {
    mockApi({
      "/approvals": terminalApprovals,
      "/tickets": tickets,
    });

    render(await ApprovalsPage({ searchParams: Promise.resolve({ status: "all" }) }));

    expect(screen.getByText("Approved; mock mutation executed")).toBeInTheDocument();
    expect(
      screen.getByText("Rejected by human reviewer; no mock mutation executed"),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Approve" })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "Reject" })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "Approve" })[0]).toBeDisabled();
    expect(screen.getAllByRole("button", { name: "Reject" })[1]).toBeDisabled();
    expect(screen.getAllByRole("button", { name: "Approve" })[0]).toHaveClass(
      "disabled:cursor-not-allowed",
    );
    expect(screen.getAllByRole("button", { name: "Reject" })[1]).toHaveClass(
      "disabled:cursor-not-allowed",
    );
    expect(screen.getAllByText("Decided by Demo Approver (Approver)")).toHaveLength(2);
  });

  it("keeps approval controls visible but disabled for the support operator", async () => {
    vi.mocked(requireDemoSession).mockResolvedValueOnce({
      accessToken: "operator-token",
      principal: {
        subject: "demo-support-operator",
        display_name: "Demo Support Operator",
        role: "support_operator",
      },
    });
    mockApi({
      "/approvals": approvals,
      "/tickets": tickets,
    });

    render(await ApprovalsPage({}));

    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Approve" })).toHaveClass(
      "disabled:cursor-not-allowed",
    );
    expect(screen.getByRole("button", { name: "Reject" })).toHaveClass(
      "disabled:cursor-not-allowed",
    );
    expect(screen.getByRole("button", { name: "Approve" })).toHaveAttribute(
      "title",
      "Requires the approver or admin role",
    );
  });

  it("recovers from a protected approval read 401 instead of rendering a data error", async () => {
    vi.mocked(handleProtectedApiError).mockImplementationOnce(() => {
      throw new Error("SESSION_RECOVERY:/approvals");
    });
    mockApi({
      "/approvals": new Response(
        JSON.stringify({
          code: "auth.invalid_token",
          message: "Invalid token",
          details: {},
          request_id: "req_expired",
        }),
        { headers: { "Content-Type": "application/json" }, status: 401 },
      ),
      "/tickets": tickets,
    });

    await expect(ApprovalsPage({})).rejects.toThrow("SESSION_RECOVERY:/approvals");
    expect(handleProtectedApiError).toHaveBeenCalledWith(
      expect.objectContaining({ code: "auth.invalid_token", status: 401 }),
      "/approvals",
    );
  });

  it("renders all nine eval cases with no preview result before M4 runs", async () => {
    mockApi({
      "/eval-cases": evalCases,
      "/eval-results": [],
      "/eval-regression/summary": evalRegressionSummary,
    });

    render(await EvalLabPage());

    expect(screen.getByRole("banner")).toHaveClass("sticky");
    expect(screen.getByRole("link", { name: "Ticket Workbench" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Approval Queue" })).toHaveAttribute(
      "href",
      "/approvals",
    );
    expect(screen.getByRole("link", { name: "Eval Lab" })).toHaveAttribute("href", "/eval-lab");
    expect(screen.getByText("Postgres reachable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Eval Lab" })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(9);
    expect(screen.getAllByText("No run yet")).toHaveLength(9);
    expect(screen.getByRole("button", { name: "Run all evals" })).toBeEnabled();
    expect(screen.getAllByRole("button", { name: /^Rerun / })).toHaveLength(9);
  });

  it("keeps Eval controls visible but disabled for a non-admin", async () => {
    vi.mocked(requireDemoSession).mockResolvedValueOnce({
      accessToken: "approver-token",
      principal: {
        subject: "demo-approver",
        display_name: "Demo Approver",
        role: "approver",
      },
    });
    mockApi({
      "/eval-cases": evalCases,
      "/eval-results": [],
      "/eval-regression/summary": evalRegressionSummary,
    });

    render(await EvalLabPage());

    expect(screen.getByRole("button", { name: "Run all evals" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Run all evals" })).toHaveAttribute(
      "title",
      "Requires the admin role",
    );
    expect(screen.getAllByRole("button", { name: /^Rerun / })).toHaveLength(9);
    for (const button of screen.getAllByRole("button", { name: /^Rerun / })) {
      expect(button).toBeDisabled();
    }
  });

  it("renders M4 eval result details and compact trace references", async () => {
    mockApi({
      "/eval-cases": evalCases,
      "/eval-results": evalResults,
      "/eval-regression/summary": evalRegressionSummary,
    });

    render(await EvalLabPage());

    const passedEval = screen.getByRole("article", { name: "eval-duplicate-charge-001" });
    const blockedEval = screen.getByRole("article", { name: "eval-usage-spike-001" });

    expect(screen.getByText("Passed")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
    expect(within(passedEval).getByText("Deterministic eval checks passed.")).toBeInTheDocument();
    expect(
      within(blockedEval).getAllByText("Scenario runner is not implemented for this scenario"),
    ).toHaveLength(2);
    expect(within(blockedEval).getByText("Blocked reason")).toBeInTheDocument();
    expect(within(passedEval).getByText("outcome correctness: pass")).toBeInTheDocument();
    expect(within(passedEval).getByText("governance compliance: pass")).toBeInTheDocument();
    expect(within(passedEval).getByText("tool planning: pass")).toBeInTheDocument();
    expect(within(passedEval).getByText("draft quality: not_run")).toBeInTheDocument();
    expect(within(passedEval).getByText("Model: fake-eval-model")).toBeInTheDocument();
    expect(within(passedEval).getByText("Prompt: m3-duplicate-charge-v1")).toBeInTheDocument();
    expect(
      within(passedEval).getByText("Trace refs: trace-eval-001 (read.billing_evidence)"),
    ).toBeInTheDocument();
    expect(within(blockedEval).getByText("Missing evidence: invoice, policy")).toBeInTheDocument();
    expect(within(blockedEval).getByText("Blocked code: scenario.runner_not_implemented")).toBeInTheDocument();
    expect(
      within(blockedEval).getByText("Readiness gaps: usage meter evidence model, pricing evidence model"),
    ).toBeInTheDocument();
    expect(
      within(blockedEval).getByText("Recommended next scenario: usage_spike"),
    ).toBeInTheDocument();
  });
});
