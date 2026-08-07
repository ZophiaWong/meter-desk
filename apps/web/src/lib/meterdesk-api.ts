import type { DemoPrincipal } from "@/lib/demo-auth";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export type DemoIdentity = DemoPrincipal;

export type DemoLoginResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  principal: DemoPrincipal;
};

export type Scenario = "duplicate_charge" | "usage_spike" | "credit_refund_dispute";

export type MoneyAmount = {
  amount_cents: number;
  currency: string;
  display: string;
};

export type TicketSummaryResource = {
  id: string;
  title: string;
  customer: string;
  status: string;
  summary: string;
  scenario: Scenario;
  is_active: boolean;
};

export type TicketDetailResource = {
  id: string;
  title: string;
  scenario: Scenario;
  status: string;
  severity: string;
  opened_at: string;
  opened_at_display: string;
  summary: string;
  outcome: string;
  customer: {
    id: string;
    name: string;
    plan: string;
    owner: string;
    status: string;
  };
};

export type BillingEvidenceResource = {
  account: TicketDetailResource["customer"];
  invoice: {
    id: string;
    period_start: string;
    period_end: string;
    period_display: string;
    total: MoneyAmount;
    status: string;
  };
  charges: Array<{
    id: string;
    status: string;
    amount: MoneyAmount;
    captured_at: string;
    captured_at_display: string;
    processor_state: string;
  }>;
  credits: Array<{
    id: string;
    label: string;
    detail: string;
    amount: MoneyAmount | null;
    granted_amount?: MoneyAmount | null;
    consumed_amount?: MoneyAmount | null;
    remaining_amount?: MoneyAmount | null;
    disputed_amount?: MoneyAmount | null;
  }>;
  usage: Array<{
    id: string;
    label: string;
    detail: string;
    period_start: string | null;
    period_end: string | null;
  }>;
  policy: {
    id: string;
    version: string;
    citation: string;
    title: string;
    reason: string;
  };
  policies?: Array<{
    id: string;
    version: string;
    citation: string;
    title: string;
    reason: string;
  }>;
  subscription?: {
    id: string;
    label: string;
    status: string;
    trial_started_at_display: string;
    trial_ended_at_display: string;
    canceled_at_display: string | null;
    renewal_captured_at_display: string | null;
    canceled_before_renewal_capture: boolean;
  } | null;
};

export type DecisionSummaryState =
  | "not_started"
  | "investigating"
  | "needs_retry"
  | "awaiting_approval"
  | "completed_no_action"
  | "rejected"
  | "mock_executed"
  | "failed"
  | "cancelled";

export type DecisionSummaryTileKind = "decision" | "evidence" | "risk_gate" | "draft";

export type DecisionSummaryTone = "neutral" | "info" | "success" | "warning" | "danger";

export type DecisionSummaryTileResource = {
  kind: DecisionSummaryTileKind;
  label: string;
  title: string;
  body: string;
  tone: DecisionSummaryTone;
  refs: string[];
};

export type AgentDecisionSummaryResource = {
  ticket_id: string;
  state: DecisionSummaryState;
  decision_label: string;
  rationale: string;
  run_id: string | null;
  workflow_id: string | null;
  workflow_version: number | null;
  workflow_status_reason_code: string | null;
  workflow_status_reason: string | null;
  approval_id: string | null;
  mutation_id: string | null;
  policy_citation: string | null;
  compliance_status: "passed" | "failed" | "unsupported" | null;
  tiles: DecisionSummaryTileResource[];
};

export type AgentRunResource = {
  id: string;
  ticket_id: string;
  workflow_id: string | null;
  idempotency_key: string | null;
  status: string;
  source: string;
  final_outcome: string | null;
  internal_resolution: string | null;
  customer_reply: string | null;
  error_state: string | null;
  error_code: string | null;
  model: string | null;
  prompt_version: string | null;
};

export type ToolTraceResource = {
  id: string;
  agent_run_id: string;
  sequence: number;
  category: string;
  risk: "Low" | "Medium" | "High";
  label: string;
  input_summary: string;
  output_summary: string;
  evidence_refs: string[];
  policy_refs: string[];
  approval_refs: string[];
  error_state: string | null;
  governance_metadata?: {
    schema_version?: string;
    policy_id?: string;
    policy_version?: string;
    risk?: "Low" | "Medium" | "High";
    gate?: string;
    gate_result?: string;
    enforcement_outcome?: string;
    required_ref_categories?: string[];
    satisfied_ref_categories?: string[];
    missing_ref_categories?: string[];
    negative_evidence_refs?: string[];
    trace_required?: boolean;
    reason_code?: string;
    planning?: Record<string, unknown>;
  };
};

export type ToolPolicyResource = {
  id: string;
  label: string;
  category: string;
  risk: "Low" | "Medium" | "High";
  executor: string;
  gate: string;
  required_evidence_refs: string[];
  requires_policy_refs: boolean;
  requires_approval_ref: boolean;
  trace_required: boolean;
  eval_dimensions: string[];
  version: string;
};

export type ApprovalResource = {
  id: string;
  ticket_id: string;
  workflow_id: string | null;
  agent_run_id: string | null;
  title: string;
  status: string;
  action_type: string;
  amount: MoneyAmount;
  reason: string;
  policy_citation: string;
  blocker: string;
  evidence_refs: string[];
  action_metadata: Record<string, unknown>;
  action_fingerprint: string;
  decided_at: string | null;
  decision: string | null;
  decision_actor: {
    subject: string | null;
    display_name: string | null;
    role: DemoPrincipal["role"] | null;
    source: "demo_session" | "seed_fixture" | "legacy_unverified";
  } | null;
  decision_request_id: string | null;
  decision_note: string | null;
};

export type MockMutationResource = {
  id: string;
  ticket_id: string;
  workflow_id: string | null;
  approval_request_id: string | null;
  agent_run_id: string | null;
  mutation_type: string;
  status: string;
  amount: MoneyAmount;
  reason: string;
  action_metadata: Record<string, unknown>;
  action_fingerprint: string;
  executed_at: string;
  executed_at_display: string;
};

export type CaseWorkflowResource = {
  id: string;
  ticket_id: string;
  cycle_number: number;
  status: Exclude<DecisionSummaryState, "not_started">;
  status_reason_code: string;
  status_reason: string | null;
  origin: string;
  previous_workflow_id: string | null;
  version: number;
  transition_sequence: number;
  created_at: string;
  updated_at: string;
  started_at: string;
  terminal_at: string | null;
};

export type CaseWorkflowTransitionResource = {
  id: string;
  workflow_id: string;
  sequence: number;
  from_status: CaseWorkflowResource["status"] | null;
  to_status: CaseWorkflowResource["status"];
  reason_code: string;
  reason_detail: string | null;
  actor_subject: string | null;
  actor_display_name: string | null;
  actor_role: DemoPrincipal["role"] | null;
  actor_source: string;
  request_id: string;
  agent_run_id: string | null;
  approval_request_id: string | null;
  mock_mutation_id: string | null;
  created_at: string;
};

export type ApprovalDecisionResponseResource = {
  approval: ApprovalResource;
  mock_mutation: MockMutationResource | null;
};

export type EvalCaseResource = {
  id: string;
  scenario: Scenario;
  title: string;
  description: string;
  expected_outcome: string;
  required_evidence: string[];
  policy_refs: string[];
  expected_approval_routing: string;
  fixture_ticket_id: string | null;
};

export type EvalTraceRef = {
  id: string;
  category: string;
  evidence_refs?: string[];
  policy_refs?: string[];
};

export type RunComplianceFailureResource = {
  code: string;
  message: string;
  affected_trace_ids: string[];
  missing_ref_categories: string[];
  approval_ids: string[];
  mutation_ids: string[];
  action_fingerprints: string[];
};

export type RunComplianceResource = {
  status: "passed" | "failed" | "unsupported";
  checked_at: string;
  failed_checks: RunComplianceFailureResource[];
  reason_codes: string[];
  affected_trace_ids: string[];
  missing_ref_categories: string[];
  policy_versions_seen: Record<string, string>;
  high_risk_gate_count: number;
  verified_governed_action_count: number;
};

export type EvalResultDetailsResource = {
  failed_checks?: string[];
  missing_evidence?: string[];
  policy_refs_seen?: string[];
  trace_refs?: EvalTraceRef[];
  blocked_reason?: string | null;
  blocked_code?: string | null;
  readiness_gaps?: string[];
  recommended_next_scenario?: string | null;
  compliance?: RunComplianceResource | null;
  judge_notes?: string[];
  model?: string | null;
  prompt_version?: string | null;
};

export type EvalResultResource = {
  id: string;
  case_id: string;
  agent_run_id: string | null;
  status: string;
  summary: string;
  dimension_scores: Record<string, string>;
  details: EvalResultDetailsResource;
};

export type EvalRunResource = {
  id: string;
  run_type: "baseline" | "suite" | "case_rerun";
  status: string;
  summary: string;
  baseline_name: string | null;
  case_id: string | null;
  started_at: string;
  completed_at: string | null;
};

export type EvalResultSnapshotResource = {
  id: string;
  eval_run_id: string;
  result_id: string;
  case_id: string;
  agent_run_id: string | null;
  snapshot_type: "baseline" | "current";
  status: string;
  summary: string;
  dimension_scores: Record<string, string>;
  details: EvalResultDetailsResource;
  trace_signature: Record<string, unknown>;
  version_snapshot: Record<string, unknown>;
  explanations: string[];
  created_at: string;
};

export type EvalRegressionCaseResource = {
  case_id: string;
  scenario: Scenario;
  title: string;
  label: "regressed" | "improved" | "unchanged" | "incomparable" | "coverage_gap";
  baseline_status: string | null;
  current_status: string | null;
  baseline_snapshot_id: string | null;
  current_snapshot_id: string | null;
  dimension_diffs: Array<{ dimension: string; baseline: string | null; current: string | null }>;
  version_diffs: Array<{ field: string; baseline: unknown; current: unknown }>;
  trace_diff: Record<string, unknown>;
  explanations: string[];
};

export type EvalRegressionSummaryResource = {
  baseline_run_id: string | null;
  baseline_name: string | null;
  latest_run_id: string | null;
  latest_run_type: "baseline" | "suite" | "case_rerun" | null;
  latest_run_completed_at: string | null;
  counts: Record<"regressed" | "improved" | "unchanged" | "incomparable" | "coverage_gap", number>;
  blocking_pass_rate: string;
  cases: EvalRegressionCaseResource[];
};

export class MeterDeskApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly code = "api.request_failed",
    readonly details: Record<string, unknown> = {},
    readonly requestId?: string,
  ) {
    super(message);
  }
}

type StructuredApiError = {
  code?: unknown;
  message?: unknown;
  details?: unknown;
  request_id?: unknown;
};

async function buildApiError(response: Response, path: string): Promise<MeterDeskApiError> {
  const fallbackMessage = `FastAPI request failed for ${path}`;
  try {
    const payload = (await response.json()) as StructuredApiError;
    if (typeof payload.code === "string" && typeof payload.message === "string") {
      return new MeterDeskApiError(
        payload.message,
        response.status,
        payload.code,
        isRecord(payload.details) ? payload.details : {},
        typeof payload.request_id === "string" ? payload.request_id : undefined,
      );
    }
  } catch {
    // Non-JSON errors keep the generic internal API error shape.
  }
  return new MeterDeskApiError(fallbackMessage, response.status);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function fetchApi<T>(
  path: string,
  apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL,
  accessToken?: string,
): Promise<T> {
  const normalizedBaseUrl = apiBaseUrl.replace(/\/$/, "");
  const headers = authorizationHeaders(accessToken);
  const response = await fetch(`${normalizedBaseUrl}${path}`, {
    cache: "no-store",
    ...(headers ? { headers } : {}),
  });

  if (!response.ok) {
    throw await buildApiError(response, path);
  }

  return (await response.json()) as T;
}

export async function postApi<T>(
  path: string,
  body?: unknown,
  apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL,
  accessToken?: string,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  const normalizedBaseUrl = apiBaseUrl.replace(/\/$/, "");
  const headers = {
    ...(authorizationHeaders(accessToken, body !== undefined) ?? {}),
    ...(extraHeaders ?? {}),
  };
  const response = await fetch(`${normalizedBaseUrl}${path}`, {
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    ...(Object.keys(headers).length > 0 ? { headers } : {}),
    method: "POST",
  });

  if (!response.ok) {
    throw await buildApiError(response, path);
  }

  return (await response.json()) as T;
}

function authorizationHeaders(
  accessToken: string | undefined,
  includeJsonContentType = false,
): Record<string, string> | undefined {
  const headers: Record<string, string> = {};
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  if (includeJsonContentType) {
    headers["Content-Type"] = "application/json";
  }
  return Object.keys(headers).length > 0 ? headers : undefined;
}

export async function getDemoIdentities(apiBaseUrl?: string) {
  return fetchApi<DemoIdentity[]>("/auth/demo-identities", apiBaseUrl);
}

export async function demoLogin(subject: string, apiBaseUrl?: string) {
  return postApi<DemoLoginResponse>("/auth/demo-login", { subject }, apiBaseUrl);
}

export async function getCurrentDemoPrincipal(accessToken: string, apiBaseUrl?: string) {
  return fetchApi<DemoPrincipal>("/auth/me", apiBaseUrl, accessToken);
}

export async function getTickets(apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<TicketSummaryResource[]>("/tickets", apiBaseUrl, accessToken);
}

export async function getTicket(ticketId: string, apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<TicketDetailResource>(`/tickets/${ticketId}`, apiBaseUrl, accessToken);
}

export async function getBillingEvidence(
  ticketId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<BillingEvidenceResource>(
    `/tickets/${ticketId}/billing-evidence`,
    apiBaseUrl,
    accessToken,
  );
}

export async function getDecisionSummary(
  ticketId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<AgentDecisionSummaryResource>(
    `/tickets/${ticketId}/decision-summary`,
    apiBaseUrl,
    accessToken,
  );
}

export async function getAgentRuns(ticketId: string, apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<AgentRunResource[]>(`/tickets/${ticketId}/agent-runs`, apiBaseUrl, accessToken);
}

export async function getTicketWorkflows(
  ticketId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<CaseWorkflowResource[]>(
    `/tickets/${ticketId}/workflows`,
    apiBaseUrl,
    accessToken,
  );
}

export async function getWorkflow(
  workflowId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<CaseWorkflowResource>(
    `/workflows/${workflowId}`,
    apiBaseUrl,
    accessToken,
  );
}

export async function getWorkflowTransitions(
  workflowId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<CaseWorkflowTransitionResource[]>(
    `/workflows/${workflowId}/transitions`,
    apiBaseUrl,
    accessToken,
  );
}

export async function cancelWorkflow(
  workflowId: string,
  reason: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return postApi<CaseWorkflowResource>(
    `/workflows/${workflowId}/cancel`,
    { reason },
    apiBaseUrl,
    accessToken,
  );
}

export async function getToolTraces(
  agentRunId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<ToolTraceResource[]>(
    `/agent-runs/${agentRunId}/traces`,
    apiBaseUrl,
    accessToken,
  );
}

export async function getRunCompliance(
  agentRunId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<RunComplianceResource>(
    `/agent-runs/${agentRunId}/compliance`,
    apiBaseUrl,
    accessToken,
  );
}

export async function getGovernanceToolPolicies(apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<ToolPolicyResource[]>("/governance/tool-policies", apiBaseUrl, accessToken);
}

export async function getApprovals(apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<ApprovalResource[]>("/approvals", apiBaseUrl, accessToken);
}

export async function getApprovalsByStatus(
  status: "pending" | "approved" | "rejected" | "withdrawn" | "all" = "pending",
  ticketId?: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  const params = new URLSearchParams({ status });
  if (ticketId) {
    params.set("ticket_id", ticketId);
  }
  return fetchApi<ApprovalResource[]>(
    `/approvals?${params.toString()}`,
    apiBaseUrl,
    accessToken,
  );
}

export async function startAgentRun(
  ticketId: string,
  apiBaseUrl?: string,
  accessToken?: string,
  idempotencyKey = crypto.randomUUID(),
) {
  return postApi<AgentRunResource>(
    `/tickets/${ticketId}/agent-runs`,
    undefined,
    apiBaseUrl,
    accessToken,
    { "Idempotency-Key": idempotencyKey },
  );
}

export async function approveRequest(
  approvalId: string,
  apiBaseUrl?: string,
  accessToken?: string,
  decisionNote?: string,
) {
  return postApi<ApprovalDecisionResponseResource>(
    `/approvals/${approvalId}/approve`,
    decisionNote ? { decision_note: decisionNote } : {},
    apiBaseUrl,
    accessToken,
  );
}

export async function rejectRequest(
  approvalId: string,
  apiBaseUrl?: string,
  accessToken?: string,
  decisionNote?: string,
) {
  return postApi<ApprovalDecisionResponseResource>(
    `/approvals/${approvalId}/reject`,
    decisionNote ? { decision_note: decisionNote } : {},
    apiBaseUrl,
    accessToken,
  );
}

export async function getMockMutations(
  ticketId?: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  const query = ticketId ? `?ticket_id=${encodeURIComponent(ticketId)}` : "";
  return fetchApi<MockMutationResource[]>(`/mock-mutations${query}`, apiBaseUrl, accessToken);
}

export async function getEvalCases(apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<EvalCaseResource[]>("/eval-cases", apiBaseUrl, accessToken);
}

export async function getEvalResults(apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<EvalResultResource[]>("/eval-results", apiBaseUrl, accessToken);
}

export async function getEvalRegressionSummary(apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<EvalRegressionSummaryResource>(
    "/eval-regression/summary",
    apiBaseUrl,
    accessToken,
  );
}

export async function getEvalRuns(apiBaseUrl?: string, accessToken?: string) {
  return fetchApi<EvalRunResource[]>("/eval-runs", apiBaseUrl, accessToken);
}

export async function getEvalRunComparison(
  evalRunId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<EvalRegressionSummaryResource>(
    `/eval-runs/${evalRunId}/comparison`,
    apiBaseUrl,
    accessToken,
  );
}

export async function getEvalCaseHistory(
  caseId: string,
  apiBaseUrl?: string,
  accessToken?: string,
) {
  return fetchApi<EvalResultSnapshotResource[]>(
    `/eval-cases/${caseId}/history`,
    apiBaseUrl,
    accessToken,
  );
}

export async function runEvalCase(caseId: string, apiBaseUrl?: string, accessToken?: string) {
  return postApi<EvalResultResource>(
    `/eval-cases/${caseId}/run`,
    undefined,
    apiBaseUrl,
    accessToken,
  );
}

export async function runAllEvalCases(apiBaseUrl?: string, accessToken?: string) {
  return postApi<EvalResultResource[]>("/eval-runs", undefined, apiBaseUrl, accessToken);
}
