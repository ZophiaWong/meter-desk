import { afterEach, describe, expect, it, vi } from "vitest";

import { getDefaultWorkbenchScenario, getEvalLabView, getWorkbenchScenario } from "./meterdesk-view";

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

    expect(scenario.traces[0].category).toBe("plan.verify");
    expect(scenario.traces[0].governance).toBe(
      "Allowed by plan.verify - Low risk - governance.allowed",
    );
    expect(scenario.traces[1].governance).toBe(
      "Allowed by read.prior_financial_actions - Low risk - governance.allowed",
    );
    expect(scenario.compliance).toEqual({
      status: "Passed",
      checkedAt: "2026-06-23T00:00:00Z",
      highRiskGateCount: 1,
      verifiedGovernedActionCount: 7,
      reasonCodes: null,
      affectedTraceIds: null,
      missingRefs: null,
      policyVersions: "plan.verify 1.0.0, read.prior_financial_actions 1.0.0",
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

  it("loads a ticket-scoped Credit/Refund Workbench scenario", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const rawUrl = input instanceof Request ? input.url : input.toString();
        const url = new URL(rawUrl);
        const payload = {
          ...payloads,
          ...creditRefundPayloads,
        }[url.pathname];
        if (payload === undefined) {
          return new Response("Not found", { status: 404 });
        }
        return new Response(JSON.stringify(payload), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        });
      }),
    );

    const scenario = await getWorkbenchScenario("TCK-1137");

    expect(scenario.ticket.id).toBe("TCK-1137");
    expect(scenario.ticket.title).toBe("Credit and refund dispute");
    expect(scenario.tickets.map((ticket) => [ticket.id, ticket.href, ticket.isActive])).toEqual([
      ["TCK-1042", "/?ticket=TCK-1042", false],
      ["TCK-1137", "/?ticket=TCK-1137", true],
    ]);
    expect(scenario.run?.promptVersion).toBe("m8-credit-refund-v1");
    expect(scenario.approval?.actionFingerprint).toBe(
      "ticket:TCK-1137|action:goodwill_credit|target:cred-ledger-1137|amount:12000|currency:USD",
    );
    expect(scenario.decisionSummary).toMatchObject({
      ticketId: "TCK-1137",
      decisionLabel: "Goodwill credit pending approval",
      policyCitation: "TRIAL-CREDIT-003 v2026.03",
    });
    expect(scenario.traces[0].category).toBe("plan.verify");
  });

  it("maps Eval Lab regression summary into compact overview and case labels", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const rawUrl = input instanceof Request ? input.url : input.toString();
        const url = new URL(rawUrl);
        const payload = evalLabPayloads[url.pathname];
        if (payload === undefined) {
          return new Response("Not found", { status: 404 });
        }
        return new Response(JSON.stringify(payload), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        });
      }),
    );

    const view = await getEvalLabView();

    expect(view.regressionSummary).toEqual({
      baselineName: "M10 seeded canonical baseline",
      latestRunId: "eval-run-latest",
      latestRunHref: "/eval-lab/runs/eval-run-latest",
      blockingPassRate: "1/1",
      counts: "0 regressed, 0 improved, 1 unchanged, 5 incomparable, 3 coverage gaps",
    });
    expect(view.cases[0]).toMatchObject({
      id: "eval-duplicate-charge-001",
      regressionLabel: "Unchanged",
      regressionTone: "success",
      regressionSummary: "No blocking regression versus seeded baseline.",
      runDetailHref: "/eval-lab/runs/eval-run-latest",
    });
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
      id: "trace-plan-verify",
      agent_run_id: "RUN-2042",
      sequence: 1,
      category: "plan.verify",
      risk: "Low",
      label: "Backend verified investigation plan contract",
      input_summary: "Checked plan.",
      output_summary: "Plan verifier accepted the investigation plan.",
      evidence_refs: ["ticket TCK-1042"],
      policy_refs: [],
      approval_refs: [],
      error_state: null,
      governance_metadata: {
        schema_version: "1.0.0",
        policy_id: "plan.verify",
        policy_version: "1.0.0",
        risk: "Low",
        gate: "Backend contract verifier accepts or blocks planned actions",
        gate_result: "allowed",
        enforcement_outcome: "trace_recorded",
        required_ref_categories: ["ticket"],
        satisfied_ref_categories: ["ticket"],
        missing_ref_categories: [],
        negative_evidence_refs: [],
        trace_required: true,
        reason_code: "governance.allowed",
      },
    },
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
      "plan.verify": "1.0.0",
      "read.prior_financial_actions": "1.0.0",
    },
    high_risk_gate_count: 1,
    verified_governed_action_count: 7,
  },
};

const creditRefundFingerprint =
  "ticket:TCK-1137|action:goodwill_credit|target:cred-ledger-1137|amount:12000|currency:USD";

const creditRefundPayloads: Record<string, unknown> = {
  "/tickets": [
    {
      id: "TCK-1042",
      title: "Same invoice charged twice",
      customer: "Northstar Compute",
      status: "Ready for approval",
      summary: "Two captured charges are attached to INV-2026-0418.",
      scenario: "duplicate_charge",
      is_active: false,
    },
    {
      id: "TCK-1137",
      title: "Credit/Refund Dispute",
      customer: "Helio SDK",
      status: "Ready for approval",
      summary: "Trial credit and cancellation timing are disputed.",
      scenario: "credit_refund_dispute",
      is_active: true,
    },
  ],
  "/tickets/TCK-1137": {
    id: "TCK-1137",
    title: "Credit and refund dispute",
    scenario: "credit_refund_dispute",
    status: "Ready for approval",
    severity: "Billing dispute",
    opened_at: "2026-06-07T10:00:00Z",
    opened_at_display: "Jun 7, 2026",
    summary: "Customer disputes how a trial credit was consumed before cancellation.",
    outcome: "Goodwill credit pending human approval.",
    customer: {
      id: "acct_helio",
      name: "Helio SDK",
      plan: "Startup API Platform",
      owner: "ops@helio.example",
      status: "Canceled after trial conversion",
    },
  },
  "/tickets/TCK-1137/billing-evidence": {
    account: {
      id: "acct_helio",
      name: "Helio SDK",
      plan: "Startup API Platform",
      owner: "ops@helio.example",
      status: "Canceled after trial conversion",
    },
    invoice: {
      id: "INV-2026-0312",
      period_start: "2026-03-01",
      period_end: "2026-03-31",
      period_display: "Mar 1-31, 2026",
      total: { amount_cents: 79000, currency: "USD", display: "$790.00" },
      status: "Paid",
    },
    charges: [
      {
        id: "ch_2026_0312_A",
        status: "Captured",
        amount: { amount_cents: 79000, currency: "USD", display: "$790.00" },
        captured_at: "2026-04-01T11:02:00Z",
        captured_at_display: "Apr 1, 2026 11:02 UTC",
        processor_state: "Linked to INV-2026-0312",
      },
    ],
    credits: [
      {
        id: "cred-ledger-1137",
        label: "Trial credit consumed before cancellation",
        detail: "$120.00 remaining trial credit is disputed.",
        amount: { amount_cents: 50000, currency: "USD", display: "$500.00" },
        disputed_amount: { amount_cents: 12000, currency: "USD", display: "$120.00" },
      },
    ],
    usage: [],
    policy: {
      id: "TRIAL-CREDIT-003",
      version: "v2026.03",
      citation: "TRIAL-CREDIT-003 v2026.03",
      title: "Trial credit and cancellation timing",
      reason: "Disputed remaining trial credits require approval.",
    },
    subscription: {
      id: "sub-helio-2026",
      label: "Trial converted before cancellation request",
      status: "Canceled after trial conversion",
      trial_started_at_display: "Feb 20, 2026",
      trial_ended_at_display: "Mar 1, 2026",
      canceled_at_display: "Mar 10, 2026",
      renewal_captured_at_display: "Apr 1, 2026 11:02 UTC",
      canceled_before_renewal_capture: false,
    },
  },
  "/tickets/TCK-1137/decision-summary": {
    ticket_id: "TCK-1137",
    state: "pending_approval",
    decision_label: "Goodwill credit pending approval",
    rationale: "The governed decision tool proposed a $120.00 goodwill credit.",
    run_id: "RUN-1137",
    approval_id: "APR-1137",
    mutation_id: null,
    policy_citation: "TRIAL-CREDIT-003 v2026.03",
    compliance_status: "passed",
    tiles: [],
  },
  "/tickets/TCK-1137/agent-runs": [
    {
      id: "RUN-1137",
      ticket_id: "TCK-1137",
      status: "completed",
      source: "seeded",
      final_outcome: "goodwill_credit_requires_approval",
      internal_resolution: "Recommend goodwill credit after approval.",
      customer_reply: "A goodwill credit request is pending approval.",
      error_state: null,
      model: "seeded-demo",
      prompt_version: "m8-credit-refund-v1",
    },
  ],
  "/agent-runs/RUN-1137/traces": [
    {
      id: "trace-1137-plan-verify",
      agent_run_id: "RUN-1137",
      sequence: 1,
      category: "plan.verify",
      risk: "Low",
      label: "Backend verified investigation plan contract",
      input_summary: "Checked plan.",
      output_summary: "Plan verifier accepted the investigation plan.",
      evidence_refs: ["ticket TCK-1137"],
      policy_refs: [],
      approval_refs: [],
      error_state: null,
      governance_metadata: {
        gate_result: "allowed",
        reason_code: "governance.allowed",
      },
    },
    {
      id: "trace-1137-read-evidence",
      agent_run_id: "RUN-1137",
      sequence: 1,
      category: "read.credit_refund_evidence",
      risk: "Low",
      label: "Collected Credit/Refund dispute evidence",
      input_summary: "Read evidence.",
      output_summary: "Found trial credit evidence.",
      evidence_refs: ["credit cred-ledger-1137", "subscription sub-helio-2026"],
      policy_refs: ["TRIAL-CREDIT-003 v2026.03"],
      approval_refs: [],
      error_state: null,
      governance_metadata: {
        gate_result: "allowed",
        reason_code: "governance.allowed",
      },
    },
  ],
  "/agent-runs/RUN-1137/compliance": {
    status: "passed",
    checked_at: "2026-06-23T00:00:00Z",
    failed_checks: [],
    reason_codes: [],
    affected_trace_ids: [],
    missing_ref_categories: [],
    policy_versions_seen: {
      "plan.verify": "1.0.0",
      "read.credit_refund_evidence": "1.0.0",
    },
    high_risk_gate_count: 1,
    verified_governed_action_count: 7,
  },
  "/approvals": [
    {
      id: "APR-1137",
      ticket_id: "TCK-1137",
      agent_run_id: "RUN-1137",
      title: "Goodwill credit pending approval",
      status: "pending",
      action_type: "goodwill_credit",
      amount: { amount_cents: 12000, currency: "USD", display: "$120.00" },
      reason: "Create a goodwill credit after approval.",
      policy_citation: "TRIAL-CREDIT-003 v2026.03",
      blocker: "Mutation blocked until human approval",
      evidence_refs: ["credit cred-ledger-1137"],
      action_metadata: { credit_ledger_entry_id: "cred-ledger-1137" },
      action_fingerprint: creditRefundFingerprint,
      decided_at: null,
      decision: null,
      decided_by: null,
      decision_note: null,
    },
  ],
  "/mock-mutations": [],
};

const evalLabPayloads: Record<string, unknown> = {
  "/eval-cases": [
    {
      id: "eval-duplicate-charge-001",
      scenario: "duplicate_charge",
      title: "Duplicate Charge golden path",
      description: "Same invoice has two captured charges.",
      expected_outcome: "confirmed_duplicate_charge",
      required_evidence: ["invoice", "charges", "policy"],
      policy_refs: ["REFUND-DUP-001 v2026.02"],
      expected_approval_routing: "refund_requires_approval",
      fixture_ticket_id: "EVAL-TCK-DUP-001",
    },
  ],
  "/eval-results": [
    {
      id: "EVAL-RESULT-1",
      case_id: "eval-duplicate-charge-001",
      agent_run_id: "RUN-EVAL-1",
      status: "passed",
      summary: "Deterministic eval checks passed.",
      dimension_scores: { outcome_correctness: "pass" },
      details: {
        failed_checks: [],
        missing_evidence: [],
        trace_refs: [{ id: "trace-1", category: "plan.verify" }],
        model: "fake-eval-model",
        prompt_version: "m3-duplicate-charge-v1",
      },
    },
  ],
  "/eval-regression/summary": {
    baseline_run_id: "EVAL-RUN-BASELINE-M10",
    baseline_name: "M10 seeded canonical baseline",
    latest_run_id: "eval-run-latest",
    latest_run_type: "case_rerun",
    latest_run_completed_at: "2026-07-01T00:00:00Z",
    counts: {
      regressed: 0,
      improved: 0,
      unchanged: 1,
      incomparable: 5,
      coverage_gap: 3,
    },
    blocking_pass_rate: "1/1",
    cases: [
      {
        case_id: "eval-duplicate-charge-001",
        scenario: "duplicate_charge",
        title: "Duplicate Charge golden path",
        label: "unchanged",
        baseline_status: "passed",
        current_status: "passed",
        baseline_snapshot_id: "EVS-BASELINE",
        current_snapshot_id: "EVS-CURRENT",
        dimension_diffs: [],
        version_diffs: [
          { field: "model", baseline: "seeded-demo", current: "fake-eval-model" },
        ],
        trace_diff: { added_categories: [], removed_categories: [] },
        explanations: ["No blocking regression versus seeded baseline."],
      },
    ],
  },
};
