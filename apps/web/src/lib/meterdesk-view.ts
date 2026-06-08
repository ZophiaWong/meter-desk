import {
  getAgentRuns,
  getApprovals,
  getBillingEvidence,
  getEvalCases,
  getEvalResults,
  getTicket,
  getTickets,
  getToolTraces,
  type ApprovalResource,
  type EvalCaseResource,
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

export type TraceEntry = {
  id: string;
  category: string;
  risk: "Low" | "Medium" | "High";
  label: string;
  output: string;
  evidence: string;
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
};

export type DraftOutputs = {
  internalResolution: string;
  customerReply: string;
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
  evidence: BillingEvidence;
  traces: TraceEntry[];
  approval: ApprovalRequest;
  drafts: DraftOutputs;
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
};

export const NAV_ITEMS: ServiceSurface[] = [
  { label: "Ticket Workbench", href: "/" },
  { label: "Approval Queue", href: "/approvals" },
  { label: "Eval Lab", href: "/eval-lab" },
];

const DEFAULT_TICKET_ID = "TCK-1042";

export async function getDefaultWorkbenchScenario(): Promise<WorkbenchScenario> {
  const [tickets, ticket, evidence, runs, approvals] = await Promise.all([
    getTickets(),
    getTicket(DEFAULT_TICKET_ID),
    getBillingEvidence(DEFAULT_TICKET_ID),
    getAgentRuns(DEFAULT_TICKET_ID),
    getApprovals(),
  ]);
  const run = runs[0];
  const traces = run ? await getToolTraces(run.id) : [];
  const approval = approvals.find((item) => item.ticket_id === DEFAULT_TICKET_ID) ?? approvals[0];

  if (!run || !approval) {
    throw new Error("Seeded Duplicate Charge run or approval is missing");
  }

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
    traces: traces.map((trace) => ({
      id: trace.id,
      category: trace.category,
      risk: trace.risk,
      label: trace.label,
      output: trace.output_summary,
      evidence: `Evidence: ${trace.evidence_refs.join(", ")}`,
    })),
    approval: mapApproval(approval),
    drafts: {
      internalResolution: run.internal_resolution,
      customerReply: run.customer_reply,
    },
  };
}

export async function getApprovalQueueItems(): Promise<ApprovalQueueItem[]> {
  const [approvals, tickets] = await Promise.all([getApprovals(), getTickets()]);
  const ticketById = new Map(tickets.map((ticket) => [ticket.id, ticket]));

  return approvals.map((approval) => ({
    id: approval.id,
    ticketId: approval.ticket_id,
    title: approval.title,
    customer: ticketById.get(approval.ticket_id)?.customer ?? approval.ticket_id,
    amount: approval.amount.display,
    status: titleCase(approval.status),
    reason: approval.reason,
    blocker: "Read-only in M2",
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
      resultStatus: result?.status ?? "No run yet",
      resultSummary: result?.summary ?? null,
    };
  });
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
    blocker: "Read-only in M2 - mutation blocked until M3 approval execution",
    policyCitation: approval.policy_citation,
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
