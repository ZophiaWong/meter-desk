import { afterEach, describe, expect, it, vi } from "vitest";

import { getDefaultWorkbenchScenario } from "./meterdesk-view";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("meterdesk-view", () => {
  it("maps M6 governance reason codes into compact trace text", async () => {
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

    const scenario = await getDefaultWorkbenchScenario();

    expect(scenario.traces[0].governance).toBe(
      "Allowed by read.prior_financial_actions - Low risk - governance.allowed",
    );
    expect(scenario.compliance).toEqual({
      status: "Passed",
      checkedAt: "2026-06-23T00:00:00Z",
      highRiskGateCount: 1,
      verifiedGovernedActionCount: 5,
      reasonCodes: null,
      affectedTraceIds: null,
      missingRefs: null,
      policyVersions: "read.prior_financial_actions 1.0.0",
    });
    expect(scenario.approval?.actionFingerprint).toBe(
      "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD",
    );
    expect(scenario.decisionSummary).toMatchObject({
      ticketId: "TCK-1042",
      state: "pending_approval",
      decisionLabel: "Duplicate captured charge confirmed",
      runId: "RUN-2042",
      approvalId: "APR-2042",
      mutationId: null,
      policyCitation: "REFUND-DUP-001 v2026.02",
      complianceStatus: "Passed",
    });
    expect(scenario.decisionSummary.tiles.map((tile) => tile.kind)).toEqual([
      "decision",
      "evidence",
      "risk_gate",
      "draft",
    ]);
  });
});

const fingerprint =
  "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD";

const payloads: Record<string, unknown> = {
  "/tickets": [
    {
      id: "TCK-1042",
      title: "Same invoice charged twice",
      customer: "Northstar Compute",
      status: "Ready for approval",
      summary: "Two captured charges are attached to INV-2026-0418.",
      scenario: "duplicate_charge",
      is_active: true,
    },
  ],
  "/tickets/TCK-1042": {
    id: "TCK-1042",
    title: "Duplicate charge investigation",
    scenario: "duplicate_charge",
    status: "Ready for approval",
    severity: "Billing dispute",
    opened_at: "2026-06-05T12:00:00Z",
    opened_at_display: "Jun 5, 2026",
    summary: "Customer reports duplicate card activity.",
    outcome: "Duplicate captured charge confirmed.",
    customer: {
      id: "acct_northstar",
      name: "Northstar Compute",
      plan: "Scale API Platform",
      owner: "billing@northstar.example",
      status: "Active",
    },
  },
  "/tickets/TCK-1042/billing-evidence": {
    account: {
      id: "acct_northstar",
      name: "Northstar Compute",
      plan: "Scale API Platform",
      owner: "billing@northstar.example",
      status: "Active",
    },
    invoice: {
      id: "INV-2026-0418",
      period_start: "2026-04-01",
      period_end: "2026-04-30",
      period_display: "Apr 1-30, 2026",
      total: { amount_cents: 124800, currency: "USD", display: "$1,248.00" },
      status: "Paid",
    },
    charges: [
      {
        id: "ch_2026_0418_B",
        status: "Captured",
        amount: { amount_cents: 124800, currency: "USD", display: "$1,248.00" },
        captured_at: "2026-05-01T09:16:00Z",
        captured_at_display: "May 1, 2026 09:16 UTC",
        processor_state: "Linked to INV-2026-0418",
      },
    ],
    credits: [],
    usage: [],
    policy: {
      id: "REFUND-DUP-001",
      version: "v2026.02",
      citation: "REFUND-DUP-001 v2026.02",
      title: "Duplicate captured payment",
      reason: "Two captured charges qualify for review.",
    },
  },
  "/tickets/TCK-1042/decision-summary": {
    ticket_id: "TCK-1042",
    state: "pending_approval",
    decision_label: "Duplicate captured charge confirmed",
    rationale:
      "Agent confirmed a duplicate captured charge on INV-2026-0418 and prepared an original refund request. The $1,248.00 mutation remains blocked until human approval.",
    run_id: "RUN-2042",
    approval_id: "APR-2042",
    mutation_id: null,
    policy_citation: "REFUND-DUP-001 v2026.02",
    compliance_status: "passed",
    tiles: [
      {
        kind: "decision",
        label: "Decision",
        title: "Duplicate captured charge confirmed",
        body: "The governed decision tool classified the duplicate payment.",
        tone: "success",
        refs: ["RUN-2042"],
      },
      {
        kind: "evidence",
        label: "Evidence",
        title: "Invoice and duplicate charge evidence",
        body: "INV-2026-0418 has duplicate captured charges.",
        tone: "info",
        refs: ["INV-2026-0418", "ch_2026_0418_B"],
      },
      {
        kind: "risk_gate",
        label: "Risk gate",
        title: "Refund blocked for approval",
        body: "APR-2042 is pending human approval.",
        tone: "warning",
        refs: ["APR-2042"],
      },
      {
        kind: "draft",
        label: "Draft",
        title: "Customer reply prepared",
        body: "Draft only - not sent.",
        tone: "neutral",
        refs: ["RUN-2042"],
      },
    ],
  },
  "/tickets/TCK-1042/agent-runs": [
    {
      id: "RUN-2042",
      ticket_id: "TCK-1042",
      status: "completed",
      source: "test",
      final_outcome: "confirmed_duplicate_charge",
      internal_resolution: "Confirmed duplicate charge.",
      customer_reply: "Draft reply.",
      error_state: null,
      model: "seeded-demo",
      prompt_version: "m3-duplicate-charge-v1",
    },
  ],
  "/approvals": [
    {
      id: "APR-2042",
      ticket_id: "TCK-1042",
      agent_run_id: "RUN-2042",
      title: "Original refund pending approval",
      status: "pending",
      action_type: "original_refund",
      amount: { amount_cents: 124800, currency: "USD", display: "$1,248.00" },
      reason: "Refund duplicate captured charge.",
      policy_citation: "REFUND-DUP-001 v2026.02",
      blocker: "Mutation blocked until human approval",
      evidence_refs: ["invoice INV-2026-0418", "charge ch_2026_0418_B"],
      action_metadata: { target_charge_id: "ch_2026_0418_B" },
      action_fingerprint: fingerprint,
      decided_at: null,
      decision: null,
      decided_by: null,
      decision_note: null,
    },
  ],
  "/mock-mutations": [],
  "/governance/tool-policies": [],
  "/agent-runs/RUN-2042/traces": [
    {
      id: "trace-prior",
      agent_run_id: "RUN-2042",
      sequence: 1,
      category: "read.prior_financial_actions",
      risk: "Low",
      label: "Checked prior approvals and mock mutations",
      input_summary: "Read existing approval and mutation state.",
      output_summary: "Found no executed mock financial actions.",
      evidence_refs: ["ticket TCK-1042"],
      policy_refs: [],
      approval_refs: [],
      error_state: null,
      governance_metadata: {
        schema_version: "1.0.0",
        policy_id: "read.prior_financial_actions",
        policy_version: "1.0.0",
        risk: "Low",
        gate: "Always allowed; trace required",
        gate_result: "allowed",
        enforcement_outcome: "trace_recorded",
        required_ref_categories: ["ticket"],
        satisfied_ref_categories: ["ticket"],
        missing_ref_categories: [],
        negative_evidence_refs: ["no_prior_mock_mutation"],
        trace_required: true,
        reason_code: "governance.allowed",
      },
    },
  ],
  "/agent-runs/RUN-2042/compliance": {
    status: "passed",
    checked_at: "2026-06-23T00:00:00Z",
    failed_checks: [],
    reason_codes: [],
    affected_trace_ids: [],
    missing_ref_categories: [],
    policy_versions_seen: {
      "read.prior_financial_actions": "1.0.0",
    },
    high_risk_gate_count: 1,
    verified_governed_action_count: 5,
  },
};
