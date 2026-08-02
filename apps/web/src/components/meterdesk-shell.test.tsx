import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MeterDeskShell } from "./meterdesk-shell";
import type { DecisionGraph, WorkbenchScenario } from "@/lib/meterdesk-view";

const checkedAt = "2026-06-05T12:00:00.000Z";
const reachableStatus = {
  api: { label: "API", state: "ok" as const, detail: "FastAPI reachable" },
  database: { label: "Postgres", state: "ok" as const, detail: "Database reachable" },
  checkedAt,
};
const adminPrincipal = {
  subject: "demo-admin",
  display_name: "Demo Admin",
  role: "admin" as const,
};

const emptyDecisionGraph: DecisionGraph = {
  defaultNodeId: "evidence" as const,
  summaryBadges: [],
  nodes: [
    {
      id: "evidence" as const,
      label: "Evidence",
      title: "Evidence loaded",
      body: "Billing evidence is available.",
      tone: "info" as const,
      status: "complete" as const,
      refs: ["INV-2026-0418"],
      traceIds: [],
      inspectorTitle: "Evidence supports the decision",
      inspectorBody: "Billing evidence is available before the governed investigation runs.",
      inspectorDetails: [],
    },
    {
      id: "policy" as const,
      label: "Policy",
      title: "Policy loaded",
      body: "Policy citation is available.",
      tone: "info" as const,
      status: "complete" as const,
      refs: ["REFUND-DUP-001 v2026.02"],
      traceIds: [],
      inspectorTitle: "Policy controls the outcome",
      inspectorBody: "Policy evidence is available before the governed investigation runs.",
      inspectorDetails: [],
    },
    {
      id: "decision" as const,
      label: "Decision",
      title: "Investigation required",
      body: "No trace-backed decision exists yet.",
      tone: "neutral" as const,
      status: "unavailable" as const,
      refs: ["TCK-1042"],
      traceIds: [],
      inspectorTitle: "No decision yet",
      inspectorBody: "A governed run is required before MeterDesk can explain the decision path.",
      inspectorDetails: [],
    },
    {
      id: "approval" as const,
      label: "Approval",
      title: "No approval request",
      body: "No approval request exists yet.",
      tone: "neutral" as const,
      status: "unavailable" as const,
      refs: [],
      traceIds: [],
      inspectorTitle: "Approval not created",
      inspectorBody: "No refund or credit approval request exists for this run.",
      inspectorDetails: [],
    },
    {
      id: "mutation" as const,
      label: "Mutation",
      title: "No mutation available",
      body: "No mock financial action can execute before approval exists.",
      tone: "neutral" as const,
      status: "unavailable" as const,
      refs: [],
      traceIds: [],
      inspectorTitle: "Mutation unavailable",
      inspectorBody: "The governed run has not created an approval-gated financial action.",
      inspectorDetails: [],
    },
  ],
  sideOutputs: [
    {
      id: "draft" as const,
      label: "Draft",
      title: "No customer draft yet",
      body: "No draft produced yet.",
      refs: [],
      traceIds: [],
    },
  ],
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
      scenario: "Duplicate Charge",
      isActive: true,
      href: "/?ticket=TCK-1042",
    },
    {
      id: "TCK-1098",
      title: "Usage Spike",
      customer: "Atlas Labs",
      status: "Seeded support scenario",
      summary: "May token usage increased after a batch import job.",
      scenario: "Usage Spike",
      isActive: false,
      href: "/?ticket=TCK-1098",
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
  decisionSummary: {
    ticketId: "TCK-1042",
    state: "not_run",
    decisionLabel: "Investigation pending",
    rationale:
      "Billing evidence is loaded for TCK-1042. Run the governed investigation to produce a trace-backed decision, approval gate, and customer draft.",
    runId: null,
    approvalId: null,
    mutationId: null,
    policyCitation: "REFUND-DUP-001 v2026.02",
    complianceStatus: null,
    tiles: [
      {
        kind: "decision",
        label: "Decision",
        title: "Investigation pending",
        body: "No agent run has produced a trace-backed recommendation yet.",
        tone: "neutral",
        refs: ["TCK-1042"],
      },
      {
        kind: "evidence",
        label: "Evidence",
        title: "Evidence loaded",
        body: "Invoice, charge, usage, credit, and policy evidence are ready for review.",
        tone: "info",
        refs: ["INV-2026-0418", "REFUND-DUP-001 v2026.02"],
      },
      {
        kind: "risk_gate",
        label: "Risk gate",
        title: "Risk gate pending",
        body: "Refund or credit mutations remain unavailable until a governed run creates an approval request.",
        tone: "warning",
        refs: [],
      },
      {
        kind: "draft",
        label: "Draft",
        title: "No customer draft yet",
        body: "Customer-facing text will remain draft-only after the agent run.",
        tone: "neutral",
        refs: [],
      },
    ],
  },
  decisionGraph: emptyDecisionGraph,
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
  compliance: null,
  traces: [],
  approval: null,
  mutations: [],
  drafts: null,
  toolPolicies: [
    {
      id: "read.billing_evidence",
      label: "Collect billing evidence",
      risk: "Low",
      executor: "backend_read_tool",
      gate: "Always allowed; trace required",
      requiredRefs: "invoice, charge, credit, usage, policy",
      approvalRequired: false,
      traceRequired: true,
      evalDimensions: "required_evidence, policy_compliance",
    },
    {
      id: "mutation.mock_refund",
      label: "Execute approved mock refund",
      risk: "High",
      executor: "backend_mutation_service",
      gate: "Requires approved approval request",
      requiredRefs: "invoice, charge, policy, approval",
      approvalRequired: true,
      traceRequired: true,
      evalDimensions: "approval_routing, mutation_safety",
    },
  ],
};

const decisionGraphFixture: DecisionGraph = {
  defaultNodeId: "mutation",
  summaryBadges: ["Plan verified", "7 governed actions", "1 approval gate"],
  nodes: [
    {
      id: "evidence",
      label: "Evidence",
      title: "Invoice and duplicate charge evidence",
      body: "INV-2026-0418 has a duplicate captured charge.",
      tone: "info",
      status: "complete",
      refs: ["INV-2026-0418", "ch_2026_0418_B"],
      traceIds: ["trace-read-evidence"],
      inspectorTitle: "Evidence supports the decision",
      inspectorBody: "The agent read invoice and charge evidence before deciding.",
      inspectorDetails: [{ label: "Trace", value: "trace-read-evidence" }],
    },
    {
      id: "policy",
      label: "Policy",
      title: "Duplicate captured payment policy",
      body: "REFUND-DUP-001 v2026.02 applies.",
      tone: "info",
      status: "complete",
      refs: ["REFUND-DUP-001 v2026.02"],
      traceIds: ["trace-decision"],
      inspectorTitle: "Policy controls the outcome",
      inspectorBody: "The decision cites the duplicate captured payment policy.",
      inspectorDetails: [{ label: "Policy", value: "REFUND-DUP-001 v2026.02" }],
    },
    {
      id: "decision",
      label: "Decision",
      title: "Duplicate captured charge confirmed",
      body: "The governed decision tool proposed an original refund.",
      tone: "success",
      status: "complete",
      refs: ["RUN-2042"],
      traceIds: ["trace-decision"],
      inspectorTitle: "Decision is trace-backed",
      inspectorBody: "The deterministic decision tool proposed a refund after evidence review.",
      inspectorDetails: [{ label: "Run", value: "RUN-2042" }],
    },
    {
      id: "approval",
      label: "Approval",
      title: "Human approval pending",
      body: "APR-2042 is pending.",
      tone: "warning",
      status: "pending",
      refs: ["APR-2042"],
      traceIds: ["trace-approval"],
      inspectorTitle: "Approval gate is active",
      inspectorBody: "The financial action waits for a human approval decision.",
      inspectorDetails: [{ label: "Approval", value: "APR-2042" }],
    },
    {
      id: "mutation",
      label: "Mutation",
      title: "Mutation blocked until approval",
      body: "Mutation blocked until human approval",
      tone: "warning",
      status: "blocked",
      refs: ["APR-2042"],
      traceIds: ["trace-approval"],
      inspectorTitle: "Mutation blocked until approval",
      inspectorBody: "No mock refund can execute until the operator approves APR-2042.",
      inspectorDetails: [{ label: "Next action", value: "Approve or reject APR-2042" }],
    },
  ],
  sideOutputs: [
    {
      id: "draft",
      label: "Draft",
      title: "Customer reply prepared",
      body: "Draft only - not sent.",
      refs: ["RUN-2042"],
      traceIds: ["trace-draft"],
    },
  ],
};

describe("MeterDeskShell", () => {
  it("renders M3 API-backed workbench data and empty run state", () => {
    render(
      <MeterDeskShell
        currentPrincipal={adminPrincipal}
        scenario={scenario}
        status={reachableStatus}
      />,
    );

    expect(screen.getByRole("link", { name: "Ticket Workbench" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Approval Queue" })).toHaveAttribute(
      "href",
      "/approvals",
    );
    expect(screen.getByRole("link", { name: "Eval Lab" })).toHaveAttribute("href", "/eval-lab");
    expect(screen.getByRole("banner")).toHaveClass("sticky");
    expect(screen.getByText("API reachable")).toBeInTheDocument();
    expect(screen.getByText("Postgres reachable")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Ticket queue" })).toBeInTheDocument();
    expect(screen.getByText("Duplicate Charge")).toBeInTheDocument();
    expect(screen.getByText("Needs approval")).toBeInTheDocument();
    expect(screen.queryByText("M3 API")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Golden path" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Decision Overview" })).toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: "Agent Decision Summary" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Safety rail" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Safety summary" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Proof & audit" })).toBeInTheDocument();
    expect(screen.getAllByText("Investigation pending").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Evidence step, Complete" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approval step, Unavailable" })).toBeInTheDocument();
    expect(screen.getAllByText("No customer draft yet").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Run investigation" })).toBeEnabled();
    expect(screen.getByRole("link", { name: /Usage Spike/ })).toHaveAttribute(
      "href",
      "/?ticket=TCK-1098",
    );
    expect(document.querySelector('input[name="ticketId"]')).toHaveAttribute("value", "TCK-1042");
    expect(screen.getByText("No agent run yet")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Mock mutation" })).getByText(
        "No mock mutation executed",
      ),
    ).toBeInTheDocument();

    const evidence = screen.getByRole("region", { name: "Billing evidence" });
    expect(within(evidence).getByText("Northstar Compute")).toBeInTheDocument();
    expect(within(evidence).getByText("INV-2026-0418")).toBeInTheDocument();
    expect(within(evidence).getByText("ch_2026_0418_A")).toBeInTheDocument();
    expect(within(evidence).getByText("ch_2026_0418_B")).toBeInTheDocument();
    expect(within(evidence).getByText("REFUND-DUP-001 v2026.02")).toBeInTheDocument();
  });

  it("renders the Decision Overview with blocked mutation selected and trace diagnostics collapsed", () => {
    render(
      <MeterDeskShell
        currentPrincipal={adminPrincipal}
        scenario={
          {
            ...scenario,
            decisionGraph: decisionGraphFixture,
            traces: [
              {
                id: "trace-approval",
                category: "approval.create_request",
                risk: "Medium",
                label: "Created approval request",
                output: "Approval request APR-2042 is pending.",
                evidence: "Evidence: invoice INV-2026-0418, charge ch_2026_0418_B",
                governance: "Allowed by approval.create_request - Medium risk",
              },
            ],
          }
        }
        status={reachableStatus}
      />,
    );

    const overview = screen.getByRole("region", { name: "Decision Overview" });
    expect(within(overview).getByText("Plan verified")).toBeInTheDocument();
    expect(within(overview).getByText("7 governed actions")).toBeInTheDocument();
    expect(within(overview).getByText("1 approval gate")).toBeInTheDocument();
    expect(within(overview).getByText("Mutation blocked until approval")).toBeInTheDocument();
    expect(
      within(overview).getByText("No mock refund can execute until the operator approves APR-2042."),
    ).toBeInTheDocument();
    expect(within(overview).getByText("Draft only - not sent.")).toBeInTheDocument();
    expect(within(overview).queryByText("->")).not.toBeInTheDocument();

    const stepper = within(overview).getByTestId("decision-stepper");
    expect(stepper.className).toContain("grid-cols-[repeat(auto-fit,minmax(10rem,1fr))]");
    expect(stepper.className).not.toContain("md:grid-cols-5");
    expect(stepper.className).not.toContain("xl:grid-cols-5");

    const evidenceStep = within(overview).getByRole("button", {
      name: "Evidence step, Complete",
    });
    expect(evidenceStep.className).toContain("min-w-0");
    expect(evidenceStep.className).toContain("min-h-[76px]");
    expect(evidenceStep.className).not.toContain("break-words");
    expect(within(evidenceStep).getByText("Evidence").className).toContain("whitespace-nowrap");

    fireEvent.click(evidenceStep);

    expect(within(overview).getByText("Evidence supports the decision")).toBeInTheDocument();
    expect(
      within(overview).getByText("The agent read invoice and charge evidence before deciding."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Allowed by approval.create_request - Medium risk")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Trace diagnostics"));

    expect(screen.getByText("Allowed by approval.create_request - Medium risk")).toBeInTheDocument();
  });

  it("renders draft-only output and active approval controls after a run", () => {
    render(
      <MeterDeskShell
        currentPrincipal={adminPrincipal}
        scenario={{
          ...scenario,
          run: {
            id: "RUN-2042",
            status: "Completed",
            model: "seeded-demo",
            promptVersion: "m3-duplicate-charge-v1",
            errorState: null,
          },
          compliance: {
            status: "Passed",
            checkedAt: "2026-06-23T00:00:00Z",
            highRiskGateCount: 1,
            verifiedGovernedActionCount: 7,
            reasonCodes: null,
            affectedTraceIds: null,
            missingRefs: null,
            policyVersions: "approval.create_request 1.0.0",
          },
          decisionSummary: {
            ticketId: "TCK-1042",
            state: "pending_approval",
            decisionLabel: "Duplicate captured charge confirmed",
            rationale:
              "Agent confirmed a duplicate captured charge on INV-2026-0418 and prepared an original refund request. The $1,248.00 mutation remains blocked until human approval.",
            runId: "RUN-2042",
            approvalId: "APR-2042",
            mutationId: null,
            policyCitation: "REFUND-DUP-001 v2026.02",
            complianceStatus: "Passed",
            tiles: [
              {
                kind: "decision",
                label: "Decision",
                title: "Duplicate captured charge confirmed",
                body: "The governed decision tool classified the duplicate payment and proposed an original refund.",
                tone: "success",
                refs: ["RUN-2042"],
              },
              {
                kind: "evidence",
                label: "Evidence",
                title: "Invoice and duplicate charge evidence",
                body: "INV-2026-0418 has captured charges ch_2026_0418_A and ch_2026_0418_B for $1,248.00.",
                tone: "info",
                refs: ["INV-2026-0418", "ch_2026_0418_A", "ch_2026_0418_B"],
              },
              {
                kind: "risk_gate",
                label: "Risk gate",
                title: "Refund blocked for approval",
                body: "APR-2042 is pending human approval; no mock mutation has executed.",
                tone: "warning",
                refs: ["APR-2042"],
              },
              {
                kind: "draft",
                label: "Draft",
                title: "Customer reply prepared",
                body: "Draft only - not sent. We are sending the duplicate charge for approval.",
                tone: "neutral",
                refs: ["RUN-2042"],
              },
            ],
          },
          traces: [
            {
              id: "trace-001",
              category: "approval.create_request",
              risk: "Medium",
              label: "Created approval request",
              output: "Approval request APR-2042 is pending.",
              evidence: "Evidence: invoice INV-2026-0418, charge ch_2026_0418_B",
              governance: "Allowed by approval.create_request - Medium risk",
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
            actionFingerprint:
              "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD",
            decisionActorSource: null,
            decisionActorSubject: null,
            decisionActorSummary: null,
            decisionNote: null,
            decisionRequestId: null,
          },
          drafts: {
            internalResolution: "Confirmed duplicate payment on INV-2026-0418.",
            customerReply: "We are sending the duplicate charge for approval.",
          },
        }}
        status={reachableStatus}
      />,
    );

    expect(screen.getAllByText("RUN-2042").length).toBeGreaterThan(0);
    expect(screen.getByRole("region", { name: "Decision Overview" })).toBeInTheDocument();
    expect(screen.getAllByText("Duplicate captured charge confirmed").length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        "Agent confirmed a duplicate captured charge on INV-2026-0418 and prepared an original refund request. The $1,248.00 mutation remains blocked until human approval.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Mutation blocked until human approval")).toBeInTheDocument();
    const safetySummary = screen.getByRole("region", { name: "Safety summary" });
    expect(within(safetySummary).getByText("Pending approval")).toBeInTheDocument();
    expect(within(safetySummary).getByText("Mutation blocked")).toBeInTheDocument();
    expect(within(safetySummary).getByText("Draft only")).toBeInTheDocument();
    expect(within(safetySummary).getByText("$1,248.00")).toBeInTheDocument();
    expect(screen.getByText("Compliance: Passed")).toBeInTheDocument();
    expect(screen.getByText("7 governed actions verified")).toBeInTheDocument();
    expect(screen.getByText("1 high-risk gate")).toBeInTheDocument();
    expect(screen.getByText("seeded-demo")).toBeInTheDocument();
    expect(screen.getByText("Prompt: m3-duplicate-charge-v1")).toBeInTheDocument();
    expect(screen.getByText("Confirmed duplicate payment on INV-2026-0418.")).toBeInTheDocument();
    expect(screen.getByText("Draft only - not sent")).toBeInTheDocument();
    const safetyRail = screen.getByRole("region", { name: "Safety rail" });
    expect(within(safetyRail).getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(within(safetyRail).getByRole("button", { name: "Reject" })).toBeEnabled();
    expect(
      within(screen.getByRole("region", { name: "Mock mutation" })).getByText(
        "No mock mutation executed",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Allowed by approval.create_request - Medium risk"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Trace diagnostics"));
    expect(screen.getByText("Allowed by approval.create_request - Medium risk")).toBeInTheDocument();
  });

  it("keeps the tool governance matrix behind a Workbench drawer", () => {
    render(
      <MeterDeskShell
        currentPrincipal={adminPrincipal}
        scenario={{
          ...scenario,
          compliance: {
            status: "Failed",
            checkedAt: "2026-06-23T00:00:00Z",
            highRiskGateCount: 0,
            verifiedGovernedActionCount: 2,
            reasonCodes: "governance.metadata_missing",
            affectedTraceIds: "trace-unsafe",
            missingRefs: "approval",
            policyVersions: "mutation.mock_refund 1.0.0",
          },
        }}
        status={reachableStatus}
      />,
    );

    const proof = screen.getByRole("region", { name: "Proof & audit" });
    expect(within(proof).getByText("Trace diagnostics")).toBeInTheDocument();
    const drawer = within(proof).getByText("2 governed actions | 1 high-risk gate | View rules");
    expect(drawer).toBeInTheDocument();

    fireEvent.click(drawer);

    expect(screen.getByText("read.billing_evidence")).toBeInTheDocument();
    expect(screen.getByText("mutation.mock_refund")).toBeInTheDocument();
    expect(screen.getByText("Requires approved approval request")).toBeInTheDocument();
    expect(screen.getByText("Compliance diagnostics")).toBeInTheDocument();
    expect(screen.getByText("Reason codes: governance.metadata_missing")).toBeInTheDocument();
    expect(screen.getByText("Affected traces: trace-unsafe")).toBeInTheDocument();
    expect(screen.getByText("Missing refs: approval")).toBeInTheDocument();
    expect(screen.getByText("Policy versions: mutation.mock_refund 1.0.0")).toBeInTheDocument();
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
        actionFingerprint:
          "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD",
        decisionActorSource: "demo_session" as const,
        decisionActorSubject: "demo-approver",
        decisionActorSummary: "Demo Approver (Approver)",
        decisionNote: "Verified duplicate charge.",
        decisionRequestId: "req_approval_demo",
      },
      mutations: [
        {
          id: "MM-2042",
          amount: "$1,248.00",
          status: "Mock executed",
          reason: "Approved original refund for duplicate captured charge.",
          executedAt: "Jun 5, 2026 12:10 UTC",
          actionFingerprint:
            "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD",
        },
      ],
    };

    const { rerender } = render(
      <MeterDeskShell
        currentPrincipal={adminPrincipal}
        scenario={failedScenario}
        status={reachableStatus}
      />,
    );

    expect(screen.getByText("Provider failed after retry: invalid structured output")).toBeInTheDocument();
    expect(screen.getByText("No approval request")).toBeInTheDocument();

    rerender(
      <MeterDeskShell
        currentPrincipal={adminPrincipal}
        scenario={approvedScenario}
        status={reachableStatus}
      />,
    );

    expect(screen.getByText("MM-2042")).toBeInTheDocument();
    expect(screen.getByText("Approved; mock mutation executed")).toBeInTheDocument();
    expect(screen.getByText("Decided by Demo Approver (Approver)")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Approval decision audit"));
    expect(screen.getByText("demo-approver")).toBeInTheDocument();
    expect(screen.getByText("req_approval_demo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
  });

  it("shows an explicit backend error instead of falling back to static data", () => {
    render(
      <MeterDeskShell
        currentPrincipal={adminPrincipal}
        dataError="FastAPI domain data unavailable"
        status={reachableStatus}
      />,
    );

    expect(screen.getByRole("heading", { name: "MeterDesk data unavailable" })).toBeInTheDocument();
    expect(screen.getByText("FastAPI domain data unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Duplicate charge investigation")).not.toBeInTheDocument();
  });

  it("shows the current identity and keeps unauthorized controls visible but disabled", () => {
    const pendingScenario: WorkbenchScenario = {
      ...scenario,
      approval: {
        id: "APR-2042",
        title: "Original refund pending approval",
        ticketId: "TCK-1042",
        amount: "$1,248.00",
        status: "Pending",
        reason: "Refund the duplicate captured charge.",
        blocker: "Mutation blocked until human approval",
        policyCitation: "REFUND-DUP-001 v2026.02",
        actionFingerprint:
          "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD",
        decisionActorSource: null,
        decisionActorSubject: null,
        decisionActorSummary: null,
        decisionNote: null,
        decisionRequestId: null,
      },
    };
    const { rerender } = render(
      <MeterDeskShell
        currentPrincipal={{
          subject: "demo-support-operator",
          display_name: "Demo Support Operator",
          role: "support_operator",
        }}
        scenario={pendingScenario}
        status={reachableStatus}
      />,
    );

    expect(screen.getByText("Demo Support Operator")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run investigation" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Approve" })).toHaveAttribute(
      "title",
      "Requires the approver or admin role",
    );

    rerender(
      <MeterDeskShell
        currentPrincipal={{
          subject: "demo-approver",
          display_name: "Demo Approver",
          role: "approver",
        }}
        scenario={pendingScenario}
        status={reachableStatus}
      />,
    );

    expect(screen.getByText("Demo Approver")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run investigation" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Run investigation" })).toHaveAttribute(
      "title",
      "Requires the support operator or admin role",
    );
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "Switch identity" })).toHaveAttribute(
      "href",
      "/login?mode=switch&returnTo=%2F",
    );
    expect(screen.getByRole("button", { name: "Log out" })).toBeInTheDocument();
  });
});
