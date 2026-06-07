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
  isPlaceholder?: boolean;
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

export type EvalDimension = {
  label: string;
  status: string;
  detail: string;
};

export type EvalSummary = {
  title: string;
  caseId: string;
  latestRun: string;
  note: string;
  dimensions: EvalDimension[];
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
  evalSummary: EvalSummary;
};

export const duplicateChargeScenario: WorkbenchScenario = {
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
      isActive: true,
    },
    {
      id: "TCK-1098",
      title: "Usage Spike",
      customer: "Atlas Labs",
      status: "M2 seed scenario",
      summary: "Supporting scenario placeholder.",
      isActive: false,
      isPlaceholder: true,
    },
    {
      id: "TCK-1137",
      title: "Credit/Refund Dispute",
      customer: "Helio SDK",
      status: "M2 seed scenario",
      summary: "Supporting scenario placeholder.",
      isActive: false,
      isPlaceholder: true,
    },
  ],
  ticket: {
    id: "TCK-1042",
    title: "Duplicate charge investigation",
    customer: "Northstar Compute",
    severity: "Billing dispute",
    openedAt: "Jun 5, 2026",
    summary:
      "Customer reports that April usage was paid once but appears twice on the card statement.",
    outcome:
      "Agent classified this as a confirmed duplicate charge and prepared an original refund request.",
  },
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
      detail: "April metered usage matches the paid invoice and does not explain a second capture.",
    },
    policy: {
      id: "REFUND-DUP-001 v2026.02",
      title: "Duplicate captured payment",
      reason: "Same invoice, same amount, and two captured charges qualify for original refund review.",
    },
  },
  traces: [
    {
      id: "trace-001",
      category: "read.billing_evidence",
      risk: "Low",
      label: "Collected invoice and charge evidence",
      output: "Found one paid invoice with two captured charges for the same amount.",
      evidence: "Evidence: invoice INV-2026-0418, charges A/B",
    },
    {
      id: "trace-002",
      category: "decision.refund_eligibility",
      risk: "Medium",
      label: "Checked duplicate refund policy",
      output: "Policy REFUND-DUP-001 applies; original refund requires human approval.",
      evidence: "Evidence: REFUND-DUP-001 v2026.02",
    },
    {
      id: "trace-003",
      category: "draft.customer_reply",
      risk: "Low",
      label: "Drafted resolution notes",
      output: "Prepared internal resolution and customer draft without promising completed refund.",
      evidence: "Evidence: approval request APR-2042",
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
  },
  drafts: {
    internalResolution:
      "Confirmed duplicate payment on INV-2026-0418. Recommend refunding ch_2026_0418_B after approval; no usage or credit anomaly explains the second capture.",
    customerReply:
      "Thanks for flagging this. We found two captured payments tied to the same April invoice. If approved, we will refund the duplicate charge to the original payment method and keep this ticket updated.",
  },
  evalSummary: {
    title: "Duplicate Charge golden path",
    caseId: "eval-duplicate-charge-001",
    latestRun: "Static M1 preview",
    note: "Trace checks inspect evidence and approval gating.",
    dimensions: [
      {
        label: "Outcome correctness",
        status: "Expected refund path",
        detail: "Final outcome classifies a confirmed duplicate charge.",
      },
      {
        label: "Policy compliance",
        status: "Policy cited",
        detail: "REFUND-DUP-001 v2026.02 controls the recommendation.",
      },
      {
        label: "Approval routing",
        status: "Approval required",
        detail: "High-risk refund mutation remains blocked while pending.",
      },
      {
        label: "Required evidence",
        status: "Evidence present",
        detail: "Invoice, charges, credit ledger, usage summary, and policy are shown.",
      },
      {
        label: "Draft quality",
        status: "Draft-only",
        detail: "Customer-facing text avoids saying the refund is complete.",
      },
    ],
  },
};
