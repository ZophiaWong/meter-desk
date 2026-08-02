import {
  getAgentRuns,
  getApprovalsByStatus,
  getBillingEvidence,
  getDecisionSummary,
  getEvalCases,
  getEvalRegressionSummary,
  getEvalResults,
  getGovernanceToolPolicies,
  getMockMutations,
  getRunCompliance,
  getTicket,
  getTickets,
  getToolTraces,
  type ApprovalResource,
  type AgentDecisionSummaryResource,
  type AgentRunResource,
  type BillingEvidenceResource,
  type EvalCaseResource,
  type EvalRegressionCaseResource,
  type MockMutationResource,
  type RunComplianceResource,
  type TicketSummaryResource,
  type ToolTraceResource,
} from "@/lib/meterdesk-api";
import { formatDemoRole } from "@/lib/demo-auth";

export type ServiceSurface = {
  label: string;
  href: string;
};

export type TicketListItem = {
  id: string;
  title: string;
  customer: string;
  status: string;
  summary: string;
  scenario: string;
  href: string;
  isActive: boolean;
};

export type BillingEvidence = {
  account: {
    name: string;
    plan: string;
    owner: string;
    status: string;
  };
  invoice: {
    id: string;
    period: string;
    total: string;
    status: string;
  };
  charges: Array<{
    id: string;
    status: string;
    amount: string;
    capturedAt: string;
    processorState: string;
  }>;
  credits: {
    label: string;
    detail: string;
  };
  usage: {
    label: string;
    detail: string;
  };
  policy: {
    id: string;
    title: string;
    reason: string;
  };
};

export type DecisionSummaryTile = {
  kind: AgentDecisionSummaryResource["tiles"][number]["kind"];
  label: string;
  title: string;
  body: string;
  tone: AgentDecisionSummaryResource["tiles"][number]["tone"];
  refs: string[];
};

export type AgentDecisionSummary = {
  ticketId: string;
  state: AgentDecisionSummaryResource["state"];
  decisionLabel: string;
  rationale: string;
  runId: string | null;
  approvalId: string | null;
  mutationId: string | null;
  policyCitation: string | null;
  complianceStatus: string | null;
  tiles: DecisionSummaryTile[];
};

export type TraceEntry = {
  id: string;
  category: string;
  risk: "Low" | "Medium" | "High";
  label: string;
  output: string;
  evidence: string;
  governance: string | null;
};

export type ApprovalRequest = {
  id: string;
  title: string;
  ticketId: string;
  amount: string;
  status: string;
  reason: string;
  blocker: string;
  policyCitation: string;
  actionFingerprint: string;
  decisionActorSource: NonNullable<ApprovalResource["decision_actor"]>["source"] | null;
  decisionActorSubject: string | null;
  decisionActorSummary: string | null;
  decisionNote: string | null;
  decisionRequestId: string | null;
};

export type AgentRunView = {
  id: string;
  status: string;
  model: string | null;
  promptVersion: string | null;
  errorState: string | null;
};

export type RunComplianceView = {
  status: string;
  checkedAt: string;
  highRiskGateCount: number;
  verifiedGovernedActionCount: number;
  reasonCodes: string | null;
  affectedTraceIds: string | null;
  missingRefs: string | null;
  policyVersions: string | null;
};

export type MockMutationView = {
  id: string;
  amount: string;
  status: string;
  reason: string;
  executedAt: string;
  actionFingerprint: string;
};

export type DraftOutputs = {
  internalResolution: string;
  customerReply: string;
};

export type DecisionGraphNodeId = "evidence" | "policy" | "decision" | "approval" | "mutation";

export type DecisionGraphStatus =
  | "complete"
  | "pending"
  | "blocked"
  | "executed"
  | "rejected"
  | "unavailable"
  | "failed";

export type DecisionGraphTone = "neutral" | "info" | "success" | "warning" | "danger";

export type DecisionGraphDetail = {
  label: string;
  value: string;
};

export type DecisionGraphNode = {
  id: DecisionGraphNodeId;
  label: string;
  title: string;
  body: string;
  tone: DecisionGraphTone;
  status: DecisionGraphStatus;
  refs: string[];
  traceIds: string[];
  inspectorTitle: string;
  inspectorBody: string;
  inspectorDetails: DecisionGraphDetail[];
};

export type DecisionGraphSideOutput = {
  id: "draft";
  label: string;
  title: string;
  body: string;
  refs: string[];
  traceIds: string[];
};

export type DecisionGraph = {
  defaultNodeId: DecisionGraphNodeId;
  summaryBadges: string[];
  nodes: DecisionGraphNode[];
  sideOutputs: DecisionGraphSideOutput[];
};

export type ToolPolicyView = {
  id: string;
  label: string;
  risk: "Low" | "Medium" | "High";
  executor: string;
  gate: string;
  requiredRefs: string;
  approvalRequired: boolean;
  traceRequired: boolean;
  evalDimensions: string;
};

export type WorkbenchScenario = {
  nav: ServiceSurface[];
  tickets: TicketListItem[];
  ticket: {
    id: string;
    title: string;
    customer: string;
    severity: string;
    openedAt: string;
    summary: string;
    outcome: string;
  };
  decisionSummary: AgentDecisionSummary;
  decisionGraph: DecisionGraph;
  evidence: BillingEvidence;
  run: AgentRunView | null;
  compliance: RunComplianceView | null;
  traces: TraceEntry[];
  approval: ApprovalRequest | null;
  mutations: MockMutationView[];
  drafts: DraftOutputs | null;
  toolPolicies: ToolPolicyView[];
};

export type ApprovalQueueItem = {
  id: string;
  ticketId: string;
  title: string;
  customer: string;
  amount: string;
  status: string;
  reason: string;
  blocker: string;
  policyCitation: string;
  decisionActorSource: ApprovalRequest["decisionActorSource"];
  decisionActorSubject: string | null;
  decisionActorSummary: string | null;
  decisionNote: string | null;
  decisionRequestId: string | null;
};

export type ApprovalQueueStatus = "pending" | "approved" | "rejected" | "all";

export type EvalCaseView = {
  id: string;
  scenario: string;
  title: string;
  description: string;
  expectedOutcome: string;
  requiredEvidence: string;
  policyRefs: string;
  approvalRouting: string;
  resultStatus: string;
  resultSummary: string | null;
  dimensions: string[];
  failedChecks: string | null;
  missingEvidence: string | null;
  blockedReason: string | null;
  blockedCode: string | null;
  readinessGaps: string | null;
  recommendedNextScenario: string | null;
  traceRefs: string | null;
  complianceReasonCodes: string | null;
  judgeNotes: string | null;
  model: string | null;
  promptVersion: string | null;
  regressionLabel: string | null;
  regressionTone: "success" | "warning" | "danger" | "neutral" | "info";
  regressionSummary: string | null;
  runDetailHref: string | null;
};

export type EvalRegressionOverview = {
  baselineName: string;
  latestRunId: string | null;
  latestRunHref: string | null;
  blockingPassRate: string;
  counts: string;
};

export type EvalLabView = {
  regressionSummary: EvalRegressionOverview;
  cases: EvalCaseView[];
};

export const NAV_ITEMS: ServiceSurface[] = [
  { label: "Ticket Workbench", href: "/" },
  { label: "Approval Queue", href: "/approvals" },
  { label: "Eval Lab", href: "/eval-lab" },
];

const DEFAULT_TICKET_ID = "TCK-1042";

export async function getDefaultWorkbenchScenario(accessToken?: string): Promise<WorkbenchScenario> {
  return getWorkbenchScenario(DEFAULT_TICKET_ID, accessToken);
}

export async function getWorkbenchScenario(
  ticketId = DEFAULT_TICKET_ID,
  accessToken?: string,
): Promise<WorkbenchScenario> {
  const [tickets, ticket, evidence, decisionSummary, runs, approvals, mutations, toolPolicies] =
    await Promise.all([
      getTickets(undefined, accessToken),
      getTicket(ticketId, undefined, accessToken),
      getBillingEvidence(ticketId, undefined, accessToken),
      getDecisionSummary(ticketId, undefined, accessToken),
      getAgentRuns(ticketId, undefined, accessToken),
      getApprovalsByStatus("all", ticketId, undefined, accessToken),
      getMockMutations(ticketId, undefined, accessToken),
      getGovernanceToolPolicies(undefined, accessToken),
    ]);
  const run = runs.at(-1) ?? null;
  const traces = run ? await getToolTraces(run.id, undefined, accessToken) : [];
  const compliance = run ? await getRunCompliance(run.id, undefined, accessToken) : null;
  const approval = approvals.at(-1) ?? null;
  const latestMutation = mutations.at(-1) ?? null;
  const drafts =
    run?.internal_resolution && run.customer_reply
      ? {
          internalResolution: run.internal_resolution,
          customerReply: run.customer_reply,
        }
      : null;
  const mappedDecisionSummary = mapDecisionSummary(decisionSummary);
  const mappedApproval = approval ? mapApproval(approval) : null;
  const mappedMutations = mutations.map((mutation) => ({
    id: mutation.id,
    amount: mutation.amount.display,
    status: titleCase(mutation.status.replace("_", " ")),
    reason: mutation.reason,
    executedAt: mutation.executed_at_display,
    actionFingerprint: mutation.action_fingerprint,
  }));

  return {
    nav: NAV_ITEMS,
    tickets: mapTickets(tickets, ticket.id),
    ticket: {
      id: ticket.id,
      title: ticket.title,
      customer: ticket.customer.name,
      severity: ticket.severity,
      openedAt: ticket.opened_at_display,
      summary: ticket.summary,
      outcome: ticket.outcome,
    },
    decisionSummary: mappedDecisionSummary,
    decisionGraph: buildDecisionGraph({
      approval,
      compliance,
      decisionSummary: mappedDecisionSummary,
      drafts,
      evidence,
      latestMutation,
      run,
      traces,
    }),
    evidence: {
      account: {
        name: evidence.account.name,
        plan: evidence.account.plan,
        owner: evidence.account.owner,
        status: evidence.account.status,
      },
      invoice: {
        id: evidence.invoice.id,
        period: evidence.invoice.period_display,
        total: evidence.invoice.total.display,
        status: evidence.invoice.status,
      },
      charges: evidence.charges.map((charge) => ({
        id: charge.id,
        status: charge.status,
        amount: charge.amount.display,
        capturedAt: charge.captured_at_display,
        processorState: charge.processor_state,
      })),
      credits: {
        label: evidence.credits[0]?.label ?? "No credit ledger entries",
        detail: evidence.credits[0]?.detail ?? "No credit evidence is available for this ticket.",
      },
      usage: {
        label: evidence.usage[0]?.label ?? "No usage records",
        detail: evidence.usage[0]?.detail ?? "No usage evidence is available for this ticket.",
      },
      policy: {
        id: evidence.policy.citation,
        title: evidence.policy.title,
        reason: evidence.policy.reason,
      },
    },
    run: run
      ? {
          id: run.id,
          status: titleCase(run.status),
          model: run.model,
          promptVersion: run.prompt_version,
          errorState: run.error_state,
        }
      : null,
    compliance: compliance ? mapCompliance(compliance) : null,
    traces: traces.map((trace) => ({
      id: trace.id,
      category: trace.category,
      risk: trace.risk,
      label: trace.label,
      output: trace.output_summary,
      evidence: `Evidence: ${trace.evidence_refs.join(", ")}`,
      governance: trace.governance_metadata?.gate_result
        ? [
            `${titleCase(trace.governance_metadata.gate_result)} by ${trace.category}`,
            `${trace.risk} risk`,
            trace.governance_metadata.reason_code,
          ]
            .filter(Boolean)
            .join(" - ")
        : null,
    })),
    approval: mappedApproval,
    mutations: mappedMutations,
    drafts,
    toolPolicies: toolPolicies.map((policy) => ({
      id: policy.id,
      label: policy.label,
      risk: policy.risk,
      executor: policy.executor,
      gate: policy.gate,
      requiredRefs: [
        ...policy.required_evidence_refs,
        ...(policy.requires_policy_refs ? ["policy"] : []),
        ...(policy.requires_approval_ref ? ["approval"] : []),
      ].join(", "),
      approvalRequired: policy.requires_approval_ref,
      traceRequired: policy.trace_required,
      evalDimensions: policy.eval_dimensions.join(", "),
    })),
  };
}

export async function getApprovalQueueItems(
  status: ApprovalQueueStatus = "pending",
  accessToken?: string,
): Promise<ApprovalQueueItem[]> {
  const [approvals, tickets] = await Promise.all([
    getApprovalsByStatus(status, undefined, undefined, accessToken),
    getTickets(undefined, accessToken),
  ]);
  const ticketById = new Map(tickets.map((ticket) => [ticket.id, ticket]));

  return approvals.map((approval) => ({
    id: approval.id,
    ticketId: approval.ticket_id,
    title: approval.title,
    customer: ticketById.get(approval.ticket_id)?.customer ?? approval.ticket_id,
    amount: approval.amount.display,
    status: titleCase(approval.status),
    reason: approval.reason,
    blocker: approval.blocker,
    policyCitation: approval.policy_citation,
    decisionActorSource: approval.decision_actor?.source ?? null,
    decisionActorSubject: approval.decision_actor?.subject ?? null,
    decisionActorSummary: formatDecisionActor(approval),
    decisionNote: approval.decision_note,
    decisionRequestId: approval.decision_request_id,
  }));
}

export async function getEvalCaseViews(accessToken?: string): Promise<EvalCaseView[]> {
  return (await getEvalLabView(accessToken)).cases;
}

export async function getEvalLabView(accessToken?: string): Promise<EvalLabView> {
  const [cases, results, regression] = await Promise.all([
    getEvalCases(undefined, accessToken),
    getEvalResults(undefined, accessToken),
    getEvalRegressionSummary(undefined, accessToken),
  ]);
  const resultByCaseId = new Map(results.map((result) => [result.case_id, result]));
  const regressionByCaseId = new Map(regression.cases.map((item) => [item.case_id, item]));
  const latestRunHref = regression.latest_run_id
    ? `/eval-lab/runs/${regression.latest_run_id}`
    : null;

  return {
    regressionSummary: {
      baselineName: regression.baseline_name ?? "No seeded baseline",
      latestRunId: regression.latest_run_id,
      latestRunHref,
      blockingPassRate: regression.blocking_pass_rate,
      counts: formatRegressionCounts(regression.counts),
    },
    cases: cases.map((evalCase) => {
      const result = resultByCaseId.get(evalCase.id);
      const regressionCase = regressionByCaseId.get(evalCase.id);
      return {
        id: evalCase.id,
        scenario: scenarioLabel(evalCase.scenario),
        title: evalCase.title,
        description: evalCase.description,
        expectedOutcome: evalCase.expected_outcome,
        requiredEvidence: evalCase.required_evidence.join(", "),
        policyRefs: evalCase.policy_refs.join(", "),
        approvalRouting: evalCase.expected_approval_routing,
        resultStatus: result ? titleCase(result.status) : "No run yet",
        resultSummary: result?.summary ?? null,
        dimensions: result
          ? Object.entries(result.dimension_scores).map(
              ([dimension, score]) => `${dimension.replaceAll("_", " ")}: ${score}`,
            )
          : [],
        failedChecks: formatList(result?.details.failed_checks),
        missingEvidence: formatList(result?.details.missing_evidence),
        blockedReason: result?.details.blocked_reason ?? null,
        blockedCode: result?.details.blocked_code ?? null,
        readinessGaps: formatList(result?.details.readiness_gaps),
        recommendedNextScenario: result?.details.recommended_next_scenario ?? null,
        traceRefs: formatTraceRefs(result?.details.trace_refs),
        complianceReasonCodes: formatList(result?.details.compliance?.reason_codes),
        judgeNotes: formatList(result?.details.judge_notes),
        model: result?.details.model ?? null,
        promptVersion: result?.details.prompt_version ?? null,
        regressionLabel: regressionCase ? regressionLabel(regressionCase) : null,
        regressionTone: regressionCase ? regressionTone(regressionCase.label) : "neutral",
        regressionSummary: regressionCase?.explanations[0] ?? null,
        runDetailHref: latestRunHref,
      };
    }),
  };
}

function mapDecisionSummary(summary: AgentDecisionSummaryResource): AgentDecisionSummary {
  return {
    ticketId: summary.ticket_id,
    state: summary.state,
    decisionLabel: summary.decision_label,
    rationale: summary.rationale,
    runId: summary.run_id,
    approvalId: summary.approval_id,
    mutationId: summary.mutation_id,
    policyCitation: summary.policy_citation,
    complianceStatus: summary.compliance_status ? titleCase(summary.compliance_status) : null,
    tiles: summary.tiles.map((tile) => ({
      kind: tile.kind,
      label: tile.label,
      title: tile.title,
      body: tile.body,
      tone: tile.tone,
      refs: tile.refs,
    })),
  };
}

function buildDecisionGraph({
  approval,
  compliance,
  decisionSummary,
  drafts,
  evidence,
  latestMutation,
  run,
  traces,
}: {
  approval: ApprovalResource | null;
  compliance: RunComplianceResource | null;
  decisionSummary: AgentDecisionSummary;
  drafts: DraftOutputs | null;
  evidence: BillingEvidenceResource;
  latestMutation: MockMutationResource | null;
  run: AgentRunResource | null;
  traces: ToolTraceResource[];
}): DecisionGraph {
  const evidenceTrace = traces.find((trace) =>
    ["read.billing_evidence", "read.credit_refund_evidence"].includes(trace.category),
  );
  const decisionTrace = traces.find((trace) => trace.category.startsWith("decision."));
  const draftTrace = traces.find((trace) => trace.category === "draft.resolution");
  const approvalTrace = traces.find((trace) => trace.category === "approval.create_request");
  const policyTraceIds = traces
    .filter(
      (trace) =>
        trace.policy_refs.length > 0 &&
        ["read.billing_evidence", "read.credit_refund_evidence", "decision.refund_eligibility", "decision.credit_refund_eligibility", "approval.create_request"].includes(
          trace.category,
        ),
    )
    .map((trace) => trace.id);
  const policyRefs = uniqueStrings([
    evidence.policy.citation,
    decisionSummary.policyCitation,
    approval?.policy_citation,
    ...traces.flatMap((trace) => trace.policy_refs),
  ]);
  const evidenceRefs = uniqueStrings([
    ...(evidenceTrace?.evidence_refs ?? []),
    `invoice ${evidence.invoice.id}`,
    ...evidence.charges.map((charge) => `charge ${charge.id}`),
    ...evidence.credits.map((credit) => `credit ${credit.id}`),
    ...evidence.usage.map((usage) => `usage ${usage.id}`),
    ...(evidence.subscription ? [`subscription ${evidence.subscription.id}`] : []),
  ]);
  const draftTile = decisionSummary.tiles.find((tile) => tile.kind === "draft");
  const graphContext = {
    approval,
    approvalTrace,
    decisionSummary,
    decisionTrace,
    evidence,
    evidenceRefs,
    evidenceTrace,
    latestMutation,
    policyRefs,
    policyTraceIds,
    run,
  };

  return {
    defaultNodeId: defaultDecisionGraphNodeId(run, approval, latestMutation),
    summaryBadges: buildDecisionGraphBadges({ compliance, traces }),
    nodes: [
      buildEvidenceNode(graphContext),
      buildPolicyNode(graphContext),
      buildDecisionNode(graphContext),
      buildApprovalNode(graphContext),
      buildMutationNode(graphContext),
    ],
    sideOutputs: [
      {
        id: "draft",
        label: "Draft",
        title: draftTile?.title ?? (drafts ? "Customer reply prepared" : "No customer draft yet"),
        body: draftTile?.body ?? (drafts ? "Draft only - not sent." : "No draft produced yet."),
        refs: draftTile?.refs.length ? draftTile.refs : run ? [run.id] : [],
        traceIds: draftTrace ? [draftTrace.id] : [],
      },
    ],
  };
}

type GraphContext = {
  approval: ApprovalResource | null;
  approvalTrace: ToolTraceResource | undefined;
  decisionSummary: AgentDecisionSummary;
  decisionTrace: ToolTraceResource | undefined;
  evidence: BillingEvidenceResource;
  evidenceRefs: string[];
  evidenceTrace: ToolTraceResource | undefined;
  latestMutation: MockMutationResource | null;
  policyRefs: string[];
  policyTraceIds: string[];
  run: AgentRunResource | null;
};

function buildEvidenceNode(context: GraphContext): DecisionGraphNode {
  const title =
    context.decisionSummary.tiles.find((tile) => tile.kind === "evidence")?.title ??
    "Billing evidence loaded";
  const body =
    context.evidenceTrace?.output_summary ??
    `${context.evidence.invoice.id} and related billing records are available.`;

  return {
    id: "evidence",
    label: "Evidence",
    title,
    body,
    tone: "info",
    status: context.evidenceTrace || context.evidenceRefs.length > 0 ? "complete" : "unavailable",
    refs: context.evidenceRefs,
    traceIds: context.evidenceTrace ? [context.evidenceTrace.id] : [],
    inspectorTitle: "Evidence supports the decision",
    inspectorBody: body,
    inspectorDetails: detailList([
      ["Invoice", context.evidence.invoice.id],
      ["Evidence refs", context.evidenceRefs.join(", ")],
      ["Trace ids", context.evidenceTrace?.id],
    ]),
  };
}

function buildPolicyNode(context: GraphContext): DecisionGraphNode {
  return {
    id: "policy",
    label: "Policy",
    title: context.evidence.policy.title,
    body:
      context.policyRefs.length > 0
        ? `${context.policyRefs.join(", ")} controls the recommendation.`
        : "No controlling policy citation is available yet.",
    tone: context.policyRefs.length > 0 ? "info" : "neutral",
    status: context.policyRefs.length > 0 ? "complete" : "unavailable",
    refs: context.policyRefs,
    traceIds: context.policyTraceIds,
    inspectorTitle: "Policy controls the outcome",
    inspectorBody: context.evidence.policy.reason,
    inspectorDetails: detailList([
      ["Policy refs", context.policyRefs.join(", ")],
      ["Trace ids", context.policyTraceIds.join(", ")],
    ]),
  };
}

function buildDecisionNode(context: GraphContext): DecisionGraphNode {
  if (!context.run) {
    return {
      id: "decision",
      label: "Decision",
      title: "Investigation required",
      body: "Run the governed investigation before a trace-backed decision graph exists.",
      tone: "neutral",
      status: "unavailable",
      refs: [context.decisionSummary.ticketId],
      traceIds: [],
      inspectorTitle: "No decision yet",
      inspectorBody: "A governed run is required before MeterDesk can explain the decision path.",
      inspectorDetails: [],
    };
  }

  if (context.run.status === "failed") {
    return {
      id: "decision",
      label: "Decision",
      title: "No reliable decision",
      body: context.run.error_state ?? "The governed investigation failed before a decision.",
      tone: "danger",
      status: "failed",
      refs: [context.run.id],
      traceIds: context.decisionTrace ? [context.decisionTrace.id] : [],
      inspectorTitle: "Decision unavailable",
      inspectorBody: context.run.error_state ?? "The run failed before producing a decision.",
      inspectorDetails: detailList([["Run", context.run.id]]),
    };
  }

  return {
    id: "decision",
    label: "Decision",
    title: context.decisionSummary.decisionLabel,
    body: context.decisionTrace?.output_summary ?? context.decisionSummary.rationale,
    tone: "success",
    status: "complete",
    refs: [context.run.id],
    traceIds: context.decisionTrace ? [context.decisionTrace.id] : [],
    inspectorTitle: "Decision is trace-backed",
    inspectorBody: context.decisionSummary.rationale,
    inspectorDetails: detailList([
      ["Run", context.run.id],
      ["Outcome", context.run.final_outcome ?? null],
      ["Trace ids", context.decisionTrace?.id],
    ]),
  };
}

function buildApprovalNode(context: GraphContext): DecisionGraphNode {
  if (!context.approval) {
    return {
      id: "approval",
      label: "Approval",
      title: "No approval request",
      body: "A financial action approval appears only after the governed run proposes one.",
      tone: "neutral",
      status: "unavailable",
      refs: [],
      traceIds: [],
      inspectorTitle: "Approval not created",
      inspectorBody: "No refund or credit approval request exists for this run.",
      inspectorDetails: [],
    };
  }

  const status = context.approval.status.toLowerCase();
  const tone = status === "approved" ? "success" : status === "rejected" ? "danger" : "warning";
  return {
    id: "approval",
    label: "Approval",
    title: context.approval.title,
    body: context.approval.blocker,
    tone,
    status: status === "approved" ? "complete" : status === "rejected" ? "rejected" : "pending",
    refs: [context.approval.id],
    traceIds: context.approvalTrace ? [context.approvalTrace.id] : [],
    inspectorTitle:
      status === "pending"
        ? "Approval gate is active"
        : status === "approved"
          ? "Approval completed"
          : "Approval rejected",
    inspectorBody: context.approval.reason,
    inspectorDetails: detailList([
      ["Approval", context.approval.id],
      ["Status", titleCase(context.approval.status)],
      ["Amount", context.approval.amount.display],
      ["Policy", context.approval.policy_citation],
      ["Decision actor", formatDecisionActor(context.approval)],
      ["Actor subject", context.approval.decision_actor?.subject],
      ["Actor source", context.approval.decision_actor?.source],
      ["Request ID", context.approval.decision_request_id],
      ["Trace ids", context.approvalTrace?.id],
    ]),
  };
}

function buildMutationNode(context: GraphContext): DecisionGraphNode {
  if (context.latestMutation) {
    return {
      id: "mutation",
      label: "Mutation",
      title: "Mock mutation executed",
      body: `${context.latestMutation.id} executed for ${context.latestMutation.amount.display}.`,
      tone: "success",
      status: "executed",
      refs: uniqueStrings([
        context.latestMutation.id,
        context.latestMutation.approval_request_id,
        context.latestMutation.action_fingerprint,
      ]),
      traceIds: [],
      inspectorTitle: "Approved mock mutation executed",
      inspectorBody: context.latestMutation.reason,
      inspectorDetails: detailList([
        ["Mutation", context.latestMutation.id],
        ["Amount", context.latestMutation.amount.display],
        ["Executed", context.latestMutation.executed_at_display],
        ["Fingerprint", context.latestMutation.action_fingerprint],
      ]),
    };
  }

  if (!context.approval) {
    return {
      id: "mutation",
      label: "Mutation",
      title: "No mutation available",
      body: "No mock financial action can execute before approval exists.",
      tone: "neutral",
      status: "unavailable",
      refs: [],
      traceIds: [],
      inspectorTitle: "Mutation unavailable",
      inspectorBody: "The governed run has not created an approval-gated financial action.",
      inspectorDetails: [],
    };
  }

  const status = context.approval.status.toLowerCase();
  if (status === "rejected") {
    return {
      id: "mutation",
      label: "Mutation",
      title: "Mutation not executed",
      body: "The human reviewer rejected the financial action; no mock mutation executed.",
      tone: "danger",
      status: "rejected",
      refs: [context.approval.id, context.approval.action_fingerprint],
      traceIds: context.approvalTrace ? [context.approvalTrace.id] : [],
      inspectorTitle: "Mutation blocked by rejection",
      inspectorBody: context.approval.blocker,
      inspectorDetails: detailList([
        ["Approval", context.approval.id],
        ["Decision", context.approval.decision ?? "rejected"],
        ["Fingerprint", context.approval.action_fingerprint],
      ]),
    };
  }

  if (status === "approved") {
    return {
      id: "mutation",
      label: "Mutation",
      title: "Mutation pending execution",
      body: "Approval is complete, but no mock mutation record is visible yet.",
      tone: "warning",
      status: "pending",
      refs: [context.approval.id, context.approval.action_fingerprint],
      traceIds: context.approvalTrace ? [context.approvalTrace.id] : [],
      inspectorTitle: "Mutation pending execution",
      inspectorBody: context.approval.blocker,
      inspectorDetails: detailList([
        ["Approval", context.approval.id],
        ["Fingerprint", context.approval.action_fingerprint],
      ]),
    };
  }

  return {
    id: "mutation",
    label: "Mutation",
    title: "Mutation blocked until approval",
    body: context.approval.blocker,
    tone: "warning",
    status: "blocked",
    refs: [context.approval.id, context.approval.action_fingerprint],
    traceIds: context.approvalTrace ? [context.approvalTrace.id] : [],
    inspectorTitle: "Mutation blocked until approval",
    inspectorBody: `No mock financial action can execute until the operator approves ${context.approval.id}.`,
    inspectorDetails: detailList([
      ["Approval", context.approval.id],
      ["Next action", `Approve or reject ${context.approval.id}`],
      ["Amount", context.approval.amount.display],
      ["Fingerprint", context.approval.action_fingerprint],
    ]),
  };
}

function defaultDecisionGraphNodeId(
  run: AgentRunResource | null,
  approval: ApprovalResource | null,
  mutation: MockMutationResource | null,
): DecisionGraphNodeId {
  if (mutation || approval) {
    return "mutation";
  }
  if (run?.status === "failed") {
    return "decision";
  }
  return "evidence";
}

function buildDecisionGraphBadges({
  compliance,
  traces,
}: {
  compliance: RunComplianceResource | null;
  traces: ToolTraceResource[];
}) {
  const badges: string[] = [];
  const planVerified = traces.some(
    (trace) =>
      trace.category === "plan.verify" &&
      (trace.output_summary.toLowerCase().includes("accepted") ||
        trace.governance_metadata?.planning?.status === "accepted"),
  );
  if (planVerified) {
    badges.push("Plan verified");
  }
  if (compliance) {
    badges.push(`${compliance.verified_governed_action_count} governed actions`);
    badges.push(
      `${compliance.high_risk_gate_count} approval ${compliance.high_risk_gate_count === 1 ? "gate" : "gates"}`,
    );
    if (compliance.status === "failed") {
      badges.push("Compliance failed");
    }
  }
  return badges;
}

function detailList(items: Array<[string, string | null | undefined]>): DecisionGraphDetail[] {
  return items
    .filter((item): item is [string, string] => Boolean(item[1]))
    .map(([label, value]) => ({ label, value }));
}

function uniqueStrings(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))));
}

function mapTickets(tickets: TicketSummaryResource[], activeTicketId: string): TicketListItem[] {
  return tickets.map((ticket) => ({
    id: ticket.id,
    title: ticket.title,
    customer: ticket.customer,
    status: ticket.status,
    summary: ticket.summary,
    scenario: scenarioLabel(ticket.scenario),
    href: `/?ticket=${encodeURIComponent(ticket.id)}`,
    isActive: ticket.id === activeTicketId,
  }));
}

function mapApproval(approval: ApprovalResource): ApprovalRequest {
  return {
    id: approval.id,
    title: approval.title,
    ticketId: approval.ticket_id,
    amount: approval.amount.display,
    status: titleCase(approval.status),
    reason: approval.reason,
    blocker: approval.blocker,
    policyCitation: approval.policy_citation,
    actionFingerprint: approval.action_fingerprint,
    decisionActorSource: approval.decision_actor?.source ?? null,
    decisionActorSubject: approval.decision_actor?.subject ?? null,
    decisionActorSummary: formatDecisionActor(approval),
    decisionNote: approval.decision_note,
    decisionRequestId: approval.decision_request_id,
  };
}

function formatDecisionActor(approval: ApprovalResource): string | null {
  const actor = approval.decision_actor;
  if (!actor) {
    return null;
  }

  const name = actor.display_name ?? actor.subject ?? "Unverified legacy actor";
  const qualifier = actor.role
    ? formatDemoRole(actor.role)
    : actor.source
        .split("_")
        .map((part) => titleCase(part))
        .join(" ");
  return `${name} (${qualifier})`;
}

function mapCompliance(compliance: RunComplianceResource): RunComplianceView {
  return {
    status: titleCase(compliance.status),
    checkedAt: compliance.checked_at,
    highRiskGateCount: compliance.high_risk_gate_count,
    verifiedGovernedActionCount: compliance.verified_governed_action_count,
    reasonCodes: formatList(compliance.reason_codes),
    affectedTraceIds: formatList(compliance.affected_trace_ids),
    missingRefs: formatList(compliance.missing_ref_categories),
    policyVersions: formatPolicyVersions(compliance.policy_versions_seen),
  };
}

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function scenarioLabel(scenario: EvalCaseResource["scenario"]): string {
  if (scenario === "duplicate_charge") {
    return "Duplicate Charge";
  }
  if (scenario === "usage_spike") {
    return "Usage Spike";
  }
  return "Credit/Refund Dispute";
}

function regressionLabel(regressionCase: EvalRegressionCaseResource): string {
  return regressionCase.label
    .split("_")
    .map((part) => titleCase(part))
    .join(" ");
}

function regressionTone(
  label: EvalRegressionCaseResource["label"],
): EvalCaseView["regressionTone"] {
  if (label === "regressed") {
    return "danger";
  }
  if (label === "improved" || label === "unchanged") {
    return "success";
  }
  if (label === "coverage_gap") {
    return "warning";
  }
  return "neutral";
}

function formatRegressionCounts(
  counts: Record<"regressed" | "improved" | "unchanged" | "incomparable" | "coverage_gap", number>,
) {
  return `${counts.regressed} regressed, ${counts.improved} improved, ${counts.unchanged} unchanged, ${counts.incomparable} incomparable, ${counts.coverage_gap} coverage gaps`;
}

function formatList(value?: string[]) {
  return value && value.length > 0 ? value.join(", ") : null;
}

function formatTraceRefs(value?: Array<{ id: string; category: string }>) {
  return value && value.length > 0
    ? value.map((trace) => `${trace.id} (${trace.category})`).join(", ")
    : null;
}

function formatPolicyVersions(value: Record<string, string>) {
  const entries = Object.entries(value);
  return entries.length > 0
    ? entries.map(([policyId, version]) => `${policyId} ${version}`).join(", ")
    : null;
}
