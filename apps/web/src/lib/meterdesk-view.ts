import {
  getAgentRuns,
  getApprovalsByStatus,
  getBillingEvidence,
  getDecisionSummary,
  getEvalCases,
  getEvalResults,
  getGovernanceToolPolicies,
  getMockMutations,
  getRunCompliance,
  getTicket,
  getTickets,
  getToolTraces,
  type ApprovalResource,
  type AgentDecisionSummaryResource,
  type EvalCaseResource,
  type RunComplianceResource,
  type TicketSummaryResource,
} from "@/lib/meterdesk-api";

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
};

export const NAV_ITEMS: ServiceSurface[] = [
  { label: "Ticket Workbench", href: "/" },
  { label: "Approval Queue", href: "/approvals" },
  { label: "Eval Lab", href: "/eval-lab" },
];

const DEFAULT_TICKET_ID = "TCK-1042";

export async function getDefaultWorkbenchScenario(): Promise<WorkbenchScenario> {
  const [tickets, ticket, evidence, decisionSummary, runs, approvals, mutations, toolPolicies] =
    await Promise.all([
      getTickets(),
      getTicket(DEFAULT_TICKET_ID),
      getBillingEvidence(DEFAULT_TICKET_ID),
      getDecisionSummary(DEFAULT_TICKET_ID),
      getAgentRuns(DEFAULT_TICKET_ID),
      getApprovalsByStatus("all", DEFAULT_TICKET_ID),
      getMockMutations(DEFAULT_TICKET_ID),
      getGovernanceToolPolicies(),
    ]);
  const run = runs.at(-1) ?? null;
  const traces = run ? await getToolTraces(run.id) : [];
  const compliance = run ? await getRunCompliance(run.id) : null;
  const approval = approvals.at(-1) ?? null;

  return {
    nav: NAV_ITEMS,
    tickets: mapTickets(tickets),
    ticket: {
      id: ticket.id,
      title: ticket.title,
      customer: ticket.customer.name,
      severity: ticket.severity,
      openedAt: ticket.opened_at_display,
      summary: ticket.summary,
      outcome: ticket.outcome,
    },
    decisionSummary: mapDecisionSummary(decisionSummary),
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
    approval: approval ? mapApproval(approval) : null,
    mutations: mutations.map((mutation) => ({
      id: mutation.id,
      amount: mutation.amount.display,
      status: titleCase(mutation.status.replace("_", " ")),
      reason: mutation.reason,
      executedAt: mutation.executed_at_display,
      actionFingerprint: mutation.action_fingerprint,
    })),
    drafts:
      run?.internal_resolution && run.customer_reply
        ? {
            internalResolution: run.internal_resolution,
            customerReply: run.customer_reply,
          }
        : null,
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
): Promise<ApprovalQueueItem[]> {
  const [approvals, tickets] = await Promise.all([getApprovalsByStatus(status), getTickets()]);
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
  }));
}

export async function getEvalCaseViews(): Promise<EvalCaseView[]> {
  const [cases, results] = await Promise.all([getEvalCases(), getEvalResults()]);
  const resultByCaseId = new Map(results.map((result) => [result.case_id, result]));

  return cases.map((evalCase) => {
    const result = resultByCaseId.get(evalCase.id);
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
    };
  });
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

function mapTickets(tickets: TicketSummaryResource[]): TicketListItem[] {
  return tickets.map((ticket) => ({
    id: ticket.id,
    title: ticket.title,
    customer: ticket.customer,
    status: ticket.status,
    summary: ticket.summary,
    isActive: ticket.is_active,
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
  };
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
