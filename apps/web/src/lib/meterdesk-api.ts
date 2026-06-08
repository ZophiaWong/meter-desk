const DEFAULT_API_BASE_URL = "http://localhost:8000";

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
};

export type AgentRunResource = {
  id: string;
  ticket_id: string;
  status: string;
  source: string;
  final_outcome: string;
  internal_resolution: string;
  customer_reply: string;
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
};

export type ApprovalResource = {
  id: string;
  ticket_id: string;
  title: string;
  status: string;
  amount: MoneyAmount;
  reason: string;
  policy_citation: string;
  blocker: string;
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
};

export type EvalResultResource = {
  id: string;
  case_id: string;
  agent_run_id: string | null;
  status: string;
  summary: string;
  dimension_scores: Record<string, string>;
};

export class MeterDeskApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

export async function fetchApi<T>(
  path: string,
  apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL,
): Promise<T> {
  const normalizedBaseUrl = apiBaseUrl.replace(/\/$/, "");
  const response = await fetch(`${normalizedBaseUrl}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new MeterDeskApiError(`FastAPI request failed for ${path}`, response.status);
  }

  return (await response.json()) as T;
}

export async function getTickets(apiBaseUrl?: string) {
  return fetchApi<TicketSummaryResource[]>("/tickets", apiBaseUrl);
}

export async function getTicket(ticketId: string, apiBaseUrl?: string) {
  return fetchApi<TicketDetailResource>(`/tickets/${ticketId}`, apiBaseUrl);
}

export async function getBillingEvidence(ticketId: string, apiBaseUrl?: string) {
  return fetchApi<BillingEvidenceResource>(`/tickets/${ticketId}/billing-evidence`, apiBaseUrl);
}

export async function getAgentRuns(ticketId: string, apiBaseUrl?: string) {
  return fetchApi<AgentRunResource[]>(`/tickets/${ticketId}/agent-runs`, apiBaseUrl);
}

export async function getToolTraces(agentRunId: string, apiBaseUrl?: string) {
  return fetchApi<ToolTraceResource[]>(`/agent-runs/${agentRunId}/traces`, apiBaseUrl);
}

export async function getApprovals(apiBaseUrl?: string) {
  return fetchApi<ApprovalResource[]>("/approvals", apiBaseUrl);
}

export async function getEvalCases(apiBaseUrl?: string) {
  return fetchApi<EvalCaseResource[]>("/eval-cases", apiBaseUrl);
}

export async function getEvalResults(apiBaseUrl?: string) {
  return fetchApi<EvalResultResource[]>("/eval-results", apiBaseUrl);
}
