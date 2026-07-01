from __future__ import annotations

from datetime import UTC, date, datetime

from meterdesk_api.agent.governance import build_governance_metadata_for_trace
from meterdesk_api.eval.regression import (
    BASELINE_NAME,
    BASELINE_RUN_ID,
    GRADER_VERSION,
    RESULT_SCHEMA_VERSION,
    build_prompt_fingerprint,
)
from meterdesk_api.eval.runner import DIMENSION_NAMES
from meterdesk_api.financial_actions import build_action_fingerprint
from meterdesk_api.repositories import InMemoryMeterDeskRepository
from meterdesk_api.schemas import (
    AgentRunSummary,
    ApprovalSummary,
    BillingEvidence,
    ChargeEvidence,
    CreditEvidence,
    CustomerSummary,
    EvalCaseSummary,
    EvalResultSnapshotSummary,
    EvalResultSummary,
    EvalRunSummary,
    InvoiceEvidence,
    MockMutationSummary,
    MoneyAmount,
    PolicyEvidence,
    SubscriptionEvidence,
    TicketDetail,
    TicketSummary,
    ToolTraceSummary,
    UsageEvidence,
)

DEMO_SEED_MARKER = "m2-demo"
DEMO_TICKET_IDS = ("TCK-1042", "TCK-1098", "TCK-1137")
EVAL_FIXTURE_TICKET_IDS = (
    "EVAL-TCK-DUP-001",
    "EVAL-TCK-DUP-002",
    "EVAL-TCK-DUP-003",
    "EVAL-TCK-CR-001",
    "EVAL-TCK-CR-002",
    "EVAL-TCK-CR-003",
)


def money(amount_cents: int, currency: str = "USD") -> MoneyAmount:
    dollars = amount_cents / 100
    return MoneyAmount(
        amount_cents=amount_cents,
        currency=currency,
        display=f"${dollars:,.2f}",
    )


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def governed_trace(**kwargs) -> ToolTraceSummary:
    governance_metadata_extra = kwargs.pop("governance_metadata_extra", None)
    governance_metadata = build_governance_metadata_for_trace(
        policy_id=kwargs["category"],
        evidence_refs=kwargs["evidence_refs"],
        policy_refs=kwargs["policy_refs"],
        approval_refs=kwargs["approval_refs"],
    )
    if governance_metadata_extra:
        governance_metadata = {**governance_metadata, **governance_metadata_extra}
    return ToolTraceSummary(
        **kwargs,
        governance_metadata=governance_metadata,
    )


def plan_investigation_metadata(
    *,
    plan_summary: str,
    steps: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "planning": {
            "status": "proposed",
            "attempt_count": 1,
            "plan_summary": plan_summary,
            "steps": steps,
            "evidence_gaps": [],
            "stop_conditions": ["Stop if required evidence is missing."],
            "blocked_attempt_reason_codes": [],
        }
    }


def plan_verify_metadata(
    *,
    normalized_action_ids: list[str],
    required_targets_seen: list[str],
) -> dict[str, object]:
    return {
        "planning": {
            "status": "accepted",
            "attempt_count": 1,
            "normalized_action_ids": normalized_action_ids,
            "required_targets_seen": required_targets_seen,
            "reason_codes": [],
            "blocked_attempt_reason_codes": [],
        }
    }


NORTHSTAR = CustomerSummary(
    id="acct_northstar",
    name="Northstar Compute",
    plan="Scale API Platform",
    owner="billing@northstar.example",
    status="Active account, no collections hold",
)

ATLAS = CustomerSummary(
    id="acct_atlas",
    name="Atlas Labs",
    plan="Growth AI Platform",
    owner="finance@atlas.example",
    status="Active account, usage alerts enabled",
)

HELIO = CustomerSummary(
    id="acct_helio",
    name="Helio SDK",
    plan="Startup API Platform",
    owner="ops@helio.example",
    status="Canceled after trial conversion",
)

TICKETS = [
    TicketSummary(
        id="TCK-1042",
        title="Same invoice charged twice",
        customer=NORTHSTAR.name,
        status="Ready for approval",
        summary="Two captured charges are attached to INV-2026-0418.",
        scenario="duplicate_charge",
        is_active=True,
    ),
    TicketSummary(
        id="TCK-1098",
        title="Usage Spike",
        customer=ATLAS.name,
        status="Seeded support scenario",
        summary="May token usage increased after a batch import job.",
        scenario="usage_spike",
    ),
    TicketSummary(
        id="TCK-1137",
        title="Credit/Refund Dispute",
        customer=HELIO.name,
        status="Seeded support scenario",
        summary="Trial credit and cancellation timing are disputed.",
        scenario="credit_refund_dispute",
    ),
]

TICKET_DETAILS = {
    "TCK-1042": TicketDetail(
        id="TCK-1042",
        title="Duplicate charge investigation",
        scenario="duplicate_charge",
        status="Ready for approval",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 5, 12),
        opened_at_display="Jun 5, 2026",
        summary=(
            "Customer reports that April usage was paid once but appears twice on the card "
            "statement."
        ),
        outcome=(
            "Seeded M5 baseline: duplicate captured charge confirmed, draft prepared, and "
            "original refund blocked behind human approval."
        ),
        customer=NORTHSTAR,
    ),
    "TCK-1098": TicketDetail(
        id="TCK-1098",
        title="Usage spike investigation",
        scenario="usage_spike",
        status="Seeded support scenario",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 6, 9),
        opened_at_display="Jun 6, 2026",
        summary="Customer asks why May usage was far above the prior baseline.",
        outcome="Seeded for later governed usage-spike investigation.",
        customer=ATLAS,
    ),
    "TCK-1137": TicketDetail(
        id="TCK-1137",
        title="Credit and refund dispute",
        scenario="credit_refund_dispute",
        status="Seeded support scenario",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 7, 10),
        opened_at_display="Jun 7, 2026",
        summary="Customer disputes how a trial credit was consumed before cancellation.",
        outcome="Seeded for later governed credit/refund investigation.",
        customer=HELIO,
    ),
}

EVAL_TICKET_DETAILS = {
    "EVAL-TCK-DUP-001": TicketDetail(
        id="EVAL-TCK-DUP-001",
        title="Eval fixture: duplicate captured charge",
        scenario="duplicate_charge",
        status="Eval fixture",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 8, 9),
        opened_at_display="Jun 8, 2026",
        summary="Eval fixture with two captured payments tied to one paid invoice.",
        outcome="Expected to require approval for an original refund.",
        customer=NORTHSTAR,
    ),
    "EVAL-TCK-DUP-002": TicketDetail(
        id="EVAL-TCK-DUP-002",
        title="Eval fixture: authorization not captured",
        scenario="duplicate_charge",
        status="Eval fixture",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 8, 10),
        opened_at_display="Jun 8, 2026",
        summary="Eval fixture with one captured payment and one uncaptured authorization.",
        outcome="Expected billing behavior; no refund or credit action.",
        customer=NORTHSTAR,
    ),
    "EVAL-TCK-DUP-003": TicketDetail(
        id="EVAL-TCK-DUP-003",
        title="Eval fixture: insufficient duplicate evidence",
        scenario="duplicate_charge",
        status="Eval fixture",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 8, 11),
        opened_at_display="Jun 8, 2026",
        summary="Eval fixture with only one captured payment linked to the invoice.",
        outcome="Expected human review because duplicate evidence is incomplete.",
        customer=NORTHSTAR,
    ),
    "EVAL-TCK-CR-001": TicketDetail(
        id="EVAL-TCK-CR-001",
        title="Eval fixture: trial credit goodwill credit",
        scenario="credit_refund_dispute",
        status="Eval fixture",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 8, 12),
        opened_at_display="Jun 8, 2026",
        summary="Eval fixture with disputed remaining trial credit after cancellation.",
        outcome="Expected to require approval for a goodwill credit.",
        customer=HELIO,
    ),
    "EVAL-TCK-CR-002": TicketDetail(
        id="EVAL-TCK-CR-002",
        title="Eval fixture: cancellation before renewal capture",
        scenario="credit_refund_dispute",
        status="Eval fixture",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 8, 13),
        opened_at_display="Jun 8, 2026",
        summary="Eval fixture where cancellation preceded the renewal capture.",
        outcome="Expected to require approval for an original refund.",
        customer=HELIO,
    ),
    "EVAL-TCK-CR-003": TicketDetail(
        id="EVAL-TCK-CR-003",
        title="Eval fixture: prior adjustment already granted",
        scenario="credit_refund_dispute",
        status="Eval fixture",
        severity="Billing dispute",
        opened_at=utc(2026, 6, 8, 14),
        opened_at_display="Jun 8, 2026",
        summary="Eval fixture where a prior goodwill credit already resolved the dispute target.",
        outcome="Expected to avoid a duplicate credit or refund.",
        customer=HELIO,
    ),
}

BILLING_EVIDENCE = {
    "TCK-1042": BillingEvidence(
        account=NORTHSTAR,
        invoice=InvoiceEvidence(
            id="INV-2026-0418",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            period_display="Apr 1-30, 2026",
            total=money(124800),
            status="Paid",
        ),
        charges=[
            ChargeEvidence(
                id="ch_2026_0418_A",
                status="Captured",
                amount=money(124800),
                captured_at=utc(2026, 5, 1, 9, 14),
                captured_at_display="May 1, 2026 09:14 UTC",
                processor_state="Linked to INV-2026-0418",
            ),
            ChargeEvidence(
                id="ch_2026_0418_B",
                status="Captured",
                amount=money(124800),
                captured_at=utc(2026, 5, 1, 9, 16),
                captured_at_display="May 1, 2026 09:16 UTC",
                processor_state="Linked to INV-2026-0418",
            ),
        ],
        credits=[
            CreditEvidence(
                id="cred-ledger-1042",
                label="Credit balance unchanged",
                detail="No prior adjustment or credit consumed against this duplicate capture.",
            )
        ],
        usage=[
            UsageEvidence(
                id="usage-2026-04-northstar",
                label="No usage spike detected",
                detail=(
                    "April metered usage matches the paid invoice and does not explain a second "
                    "capture."
                ),
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 30),
            )
        ],
        policy=PolicyEvidence(
            id="REFUND-DUP-001",
            version="v2026.02",
            citation="REFUND-DUP-001 v2026.02",
            title="Duplicate captured payment",
            reason=(
                "Same invoice, same amount, and two captured charges qualify for original refund "
                "review."
            ),
        ),
    ),
    "TCK-1098": BillingEvidence(
        account=ATLAS,
        invoice=InvoiceEvidence(
            id="INV-2026-0521",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            period_display="May 1-31, 2026",
            total=money(389600),
            status="Paid",
        ),
        charges=[
            ChargeEvidence(
                id="ch_2026_0521_A",
                status="Captured",
                amount=money(389600),
                captured_at=utc(2026, 6, 1, 8, 20),
                captured_at_display="Jun 1, 2026 08:20 UTC",
                processor_state="Linked to INV-2026-0521",
            )
        ],
        credits=[
            CreditEvidence(
                id="cred-ledger-1098",
                label="No goodwill credit applied",
                detail="No prior goodwill adjustment exists for the May usage spike.",
            )
        ],
        usage=[
            UsageEvidence(
                id="usage-2026-05-atlas",
                label="Batch import drove usage",
                detail=(
                    "Token usage increased 240% during a May 18 import job using production API "
                    "keys."
                ),
                period_start=date(2026, 5, 1),
                period_end=date(2026, 5, 31),
            )
        ],
        policy=PolicyEvidence(
            id="USAGE-SPIKE-002",
            version="v2026.01",
            citation="USAGE-SPIKE-002 v2026.01",
            title="Customer-initiated usage spikes",
            reason=(
                "Usage created by valid API keys is billable; goodwill credits require human "
                "approval."
            ),
        ),
    ),
    "TCK-1137": BillingEvidence(
        account=HELIO,
        invoice=InvoiceEvidence(
            id="INV-2026-0312",
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            period_display="Mar 1-31, 2026",
            total=money(79000),
            status="Paid",
        ),
        charges=[
            ChargeEvidence(
                id="ch_2026_0312_A",
                status="Captured",
                amount=money(79000),
                captured_at=utc(2026, 4, 1, 11, 2),
                captured_at_display="Apr 1, 2026 11:02 UTC",
                processor_state="Linked to INV-2026-0312",
            )
        ],
        credits=[
            CreditEvidence(
                id="cred-ledger-1137",
                label="Trial credit consumed before cancellation",
                detail=(
                    "$500.00 trial credit had $120.00 remaining in dispute at cancellation time "
                    "after paid conversion usage consumed the rest."
                ),
                amount=money(50000),
                granted_amount=money(50000),
                consumed_amount=money(38000),
                remaining_amount=money(12000),
                disputed_amount=money(12000),
            )
        ],
        usage=[
            UsageEvidence(
                id="usage-2026-03-helio",
                label="Usage after trial conversion",
                detail="Billable usage continued for 9 days after the trial converted to paid.",
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
            )
        ],
        policy=PolicyEvidence(
            id="TRIAL-CREDIT-003",
            version="v2026.03",
            citation="TRIAL-CREDIT-003 v2026.03",
            title="Trial credit and cancellation timing",
            reason=(
                "Disputed remaining trial credits may be issued as goodwill credit only after "
                "human approval."
            ),
        ),
        policies=[
            PolicyEvidence(
                id="TRIAL-CREDIT-003",
                version="v2026.03",
                citation="TRIAL-CREDIT-003 v2026.03",
                title="Trial credit and cancellation timing",
                reason=(
                    "Disputed remaining trial credits may be issued as goodwill credit only after "
                    "human approval."
                ),
            ),
            PolicyEvidence(
                id="CANCEL-REFUND-004",
                version="v2026.03",
                citation="CANCEL-REFUND-004 v2026.03",
                title="Cancellation before renewal capture",
                reason="Renewal captures after documented cancellation require refund review.",
            ),
            PolicyEvidence(
                id="ADJUSTMENT-LIMIT-002",
                version="v2026.03",
                citation="ADJUSTMENT-LIMIT-002 v2026.03",
                title="Prior financial adjustment limit",
                reason="Do not create a duplicate credit or refund for the same dispute target.",
            ),
        ],
        subscription=SubscriptionEvidence(
            id="sub-helio-2026",
            label="Trial converted before cancellation request",
            status="Canceled after trial conversion",
            trial_started_at_display="Feb 20, 2026",
            trial_ended_at_display="Mar 1, 2026",
            canceled_at_display="Mar 10, 2026",
            renewal_captured_at_display="Apr 1, 2026 11:02 UTC",
            canceled_before_renewal_capture=False,
        ),
    ),
}

EVAL_BILLING_EVIDENCE = {
    "EVAL-TCK-DUP-001": BILLING_EVIDENCE["TCK-1042"].model_copy(
        update={
            "invoice": BILLING_EVIDENCE["TCK-1042"].invoice.model_copy(
                update={"id": "INV-EVAL-DUP-001"}
            ),
            "charges": [
                BILLING_EVIDENCE["TCK-1042"]
                .charges[0]
                .model_copy(
                    update={
                        "id": "ch_eval_dup_001_A",
                        "processor_state": "Linked to INV-EVAL-DUP-001",
                    }
                ),
                BILLING_EVIDENCE["TCK-1042"]
                .charges[1]
                .model_copy(
                    update={
                        "id": "ch_eval_dup_001_B",
                        "processor_state": "Linked to INV-EVAL-DUP-001",
                    }
                ),
            ],
            "credits": [
                BILLING_EVIDENCE["TCK-1042"]
                .credits[0]
                .model_copy(update={"id": "cred-ledger-eval-dup-001"})
            ],
            "usage": [
                BILLING_EVIDENCE["TCK-1042"]
                .usage[0]
                .model_copy(update={"id": "usage-eval-dup-001"})
            ],
        }
    ),
    "EVAL-TCK-DUP-002": BILLING_EVIDENCE["TCK-1042"].model_copy(
        update={
            "invoice": BILLING_EVIDENCE["TCK-1042"].invoice.model_copy(
                update={"id": "INV-EVAL-DUP-002"}
            ),
            "charges": [
                BILLING_EVIDENCE["TCK-1042"]
                .charges[0]
                .model_copy(
                    update={
                        "id": "ch_eval_dup_002_A",
                        "processor_state": "Linked to INV-EVAL-DUP-002",
                    }
                ),
                BILLING_EVIDENCE["TCK-1042"]
                .charges[1]
                .model_copy(
                    update={
                        "id": "auth_eval_dup_002_B",
                        "status": "Authorized",
                        "processor_state": "Authorization only; not captured",
                    }
                ),
            ],
            "credits": [
                BILLING_EVIDENCE["TCK-1042"]
                .credits[0]
                .model_copy(update={"id": "cred-ledger-eval-dup-002"})
            ],
            "usage": [
                BILLING_EVIDENCE["TCK-1042"]
                .usage[0]
                .model_copy(update={"id": "usage-eval-dup-002"})
            ],
        }
    ),
    "EVAL-TCK-DUP-003": BILLING_EVIDENCE["TCK-1042"].model_copy(
        update={
            "invoice": BILLING_EVIDENCE["TCK-1042"].invoice.model_copy(
                update={"id": "INV-EVAL-DUP-003"}
            ),
            "charges": [
                BILLING_EVIDENCE["TCK-1042"]
                .charges[0]
                .model_copy(
                    update={
                        "id": "ch_eval_dup_003_A",
                        "processor_state": "Linked to INV-EVAL-DUP-003",
                    }
                )
            ],
            "credits": [
                BILLING_EVIDENCE["TCK-1042"]
                .credits[0]
                .model_copy(update={"id": "cred-ledger-eval-dup-003"})
            ],
            "usage": [
                BILLING_EVIDENCE["TCK-1042"]
                .usage[0]
                .model_copy(update={"id": "usage-eval-dup-003"})
            ],
        }
    ),
    "EVAL-TCK-CR-001": BILLING_EVIDENCE["TCK-1137"].model_copy(
        update={
            "invoice": BILLING_EVIDENCE["TCK-1137"].invoice.model_copy(
                update={"id": "INV-EVAL-CR-001"}
            ),
            "charges": [
                BILLING_EVIDENCE["TCK-1137"]
                .charges[0]
                .model_copy(
                    update={
                        "id": "ch_eval_cr_001_A",
                        "processor_state": "Linked to INV-EVAL-CR-001",
                    }
                )
            ],
            "credits": [
                BILLING_EVIDENCE["TCK-1137"]
                .credits[0]
                .model_copy(update={"id": "cred-ledger-eval-cr-001"})
            ],
            "usage": [
                BILLING_EVIDENCE["TCK-1137"].usage[0].model_copy(update={"id": "usage-eval-cr-001"})
            ],
            "subscription": BILLING_EVIDENCE["TCK-1137"].subscription.model_copy(
                update={"id": "sub-eval-cr-001"}
            )
            if BILLING_EVIDENCE["TCK-1137"].subscription
            else None,
        }
    ),
    "EVAL-TCK-CR-002": BILLING_EVIDENCE["TCK-1137"].model_copy(
        update={
            "invoice": BILLING_EVIDENCE["TCK-1137"].invoice.model_copy(
                update={"id": "INV-EVAL-CR-002"}
            ),
            "charges": [
                BILLING_EVIDENCE["TCK-1137"]
                .charges[0]
                .model_copy(
                    update={
                        "id": "ch_eval_cr_002_A",
                        "processor_state": "Captured after cancellation; linked to INV-EVAL-CR-002",
                    }
                )
            ],
            "credits": [
                BILLING_EVIDENCE["TCK-1137"]
                .credits[0]
                .model_copy(
                    update={
                        "id": "cred-ledger-eval-cr-002",
                        "disputed_amount": None,
                    }
                )
            ],
            "usage": [
                BILLING_EVIDENCE["TCK-1137"].usage[0].model_copy(update={"id": "usage-eval-cr-002"})
            ],
            "subscription": BILLING_EVIDENCE["TCK-1137"].subscription.model_copy(
                update={
                    "id": "sub-eval-cr-002",
                    "label": "Cancellation recorded before renewal capture",
                    "canceled_at_display": "Mar 30, 2026",
                    "canceled_before_renewal_capture": True,
                }
            )
            if BILLING_EVIDENCE["TCK-1137"].subscription
            else None,
        }
    ),
    "EVAL-TCK-CR-003": BILLING_EVIDENCE["TCK-1137"].model_copy(
        update={
            "invoice": BILLING_EVIDENCE["TCK-1137"].invoice.model_copy(
                update={"id": "INV-EVAL-CR-003"}
            ),
            "charges": [
                BILLING_EVIDENCE["TCK-1137"]
                .charges[0]
                .model_copy(
                    update={
                        "id": "ch_eval_cr_003_A",
                        "processor_state": "Linked to INV-EVAL-CR-003",
                    }
                )
            ],
            "credits": [
                BILLING_EVIDENCE["TCK-1137"]
                .credits[0]
                .model_copy(update={"id": "cred-ledger-eval-cr-003"})
            ],
            "usage": [
                BILLING_EVIDENCE["TCK-1137"].usage[0].model_copy(update={"id": "usage-eval-cr-003"})
            ],
            "subscription": BILLING_EVIDENCE["TCK-1137"].subscription.model_copy(
                update={"id": "sub-eval-cr-003"}
            )
            if BILLING_EVIDENCE["TCK-1137"].subscription
            else None,
        }
    ),
}

AGENT_RUNS = {
    "TCK-1042": [
        AgentRunSummary(
            id="RUN-2042",
            ticket_id="TCK-1042",
            status="completed",
            source="m5_seeded_demo",
            final_outcome="confirmed_duplicate_charge",
            internal_resolution=(
                "Confirmed two captured payments for INV-2026-0418. The second charge "
                "ch_2026_0418_B matches the invoice total and qualifies for an original-method "
                "refund after human approval under REFUND-DUP-001 v2026.02."
            ),
            customer_reply=(
                "Thanks for flagging this. We found two captured payments tied to the same "
                "April invoice. A refund request for the duplicate charge is pending human "
                "approval, and this reply remains a draft until your team sends it."
            ),
            model="seeded-demo",
            prompt_version="m3-duplicate-charge-v1",
        )
    ],
    "TCK-1098": [],
    "TCK-1137": [
        AgentRunSummary(
            id="RUN-1137",
            ticket_id="TCK-1137",
            status="completed",
            source="m8_credit_refund_loop",
            final_outcome="goodwill_credit_requires_approval",
            internal_resolution=(
                "Confirmed a disputed $120.00 remaining trial credit for Helio SDK after "
                "cancellation timing review. Recommend a goodwill credit after human approval "
                "under TRIAL-CREDIT-003 v2026.03."
            ),
            customer_reply=(
                "Thanks for raising this. We reviewed the trial credit ledger and cancellation "
                "timing. A goodwill credit request for the disputed remaining trial credit is "
                "pending human approval, and this reply remains a draft until your team sends it."
            ),
            model="seeded-demo",
            prompt_version="m8-credit-refund-v1",
        )
    ],
}

TRACES: dict[str, list[ToolTraceSummary]] = {
    "RUN-2042": [
        governed_trace(
            id="trace-2042-plan",
            agent_run_id="RUN-2042",
            sequence=1,
            category="plan.investigation",
            risk="Low",
            label="LLM proposed investigation tool plan",
            input_summary=(
                "Requested investigation plan for TCK-1042 before reading billing evidence."
            ),
            output_summary="Investigate duplicate-charge evidence and backend refund eligibility.",
            evidence_refs=["ticket TCK-1042"],
            policy_refs=[],
            approval_refs=[],
            governance_metadata_extra=plan_investigation_metadata(
                plan_summary=(
                    "Investigate duplicate-charge evidence and backend refund eligibility."
                ),
                steps=[
                    {
                        "step_id": "evidence",
                        "action_id": "read.billing_evidence",
                        "evidence_targets": [
                            "account_state",
                            "invoice",
                            "charges",
                            "payment_status",
                            "credit_ledger",
                            "usage",
                            "policy",
                        ],
                        "rationale": ("Read invoice, charge, credit, usage, and policy evidence."),
                        "depends_on": [],
                    },
                    {
                        "step_id": "prior",
                        "action_id": "read.prior_financial_actions",
                        "evidence_targets": ["prior_financial_actions"],
                        "rationale": ("Check prior financial actions to avoid duplicate refunds."),
                        "depends_on": [],
                    },
                    {
                        "step_id": "decision",
                        "action_id": "decision.refund_eligibility",
                        "evidence_targets": [
                            "invoice",
                            "charges",
                            "policy",
                            "prior_financial_actions",
                        ],
                        "rationale": (
                            "Ask the backend decision tool to classify refund eligibility."
                        ),
                        "depends_on": ["evidence", "prior"],
                    },
                ],
            ),
        ),
        governed_trace(
            id="trace-2042-plan-verify",
            agent_run_id="RUN-2042",
            sequence=2,
            category="plan.verify",
            risk="Low",
            label="Backend verified investigation plan contract",
            input_summary=(
                "Checked planned actions, evidence targets, dependencies, and safety scope."
            ),
            output_summary="Plan verifier accepted the investigation plan.",
            evidence_refs=["ticket TCK-1042"],
            policy_refs=[],
            approval_refs=[],
            governance_metadata_extra=plan_verify_metadata(
                normalized_action_ids=[
                    "read.billing_evidence",
                    "read.prior_financial_actions",
                    "decision.refund_eligibility",
                ],
                required_targets_seen=[
                    "account_state",
                    "invoice",
                    "charges",
                    "payment_status",
                    "credit_ledger",
                    "usage",
                    "policy",
                    "prior_financial_actions",
                ],
            ),
        ),
        governed_trace(
            id="trace-2042-read-evidence",
            agent_run_id="RUN-2042",
            sequence=3,
            category="read.billing_evidence",
            risk="Low",
            label="Collected Duplicate Charge billing evidence",
            input_summary="Read ticket, invoice, charges, credits, usage, and policy for TCK-1042.",
            output_summary=(
                "Found invoice INV-2026-0418 with 2 captured charge records and policy "
                "REFUND-DUP-001 v2026.02."
            ),
            evidence_refs=[
                "invoice INV-2026-0418",
                "charge ch_2026_0418_A",
                "charge ch_2026_0418_B",
                "credit cred-ledger-1042",
                "usage usage-2026-04-northstar",
            ],
            policy_refs=["REFUND-DUP-001 v2026.02"],
            approval_refs=[],
        ),
        governed_trace(
            id="trace-2042-prior-actions",
            agent_run_id="RUN-2042",
            sequence=4,
            category="read.prior_financial_actions",
            risk="Low",
            label="Checked prior approvals and mock mutations",
            input_summary="Read existing approval and mutation state for TCK-1042.",
            output_summary="Found 0 executed mock financial action(s).",
            evidence_refs=["ticket TCK-1042"],
            policy_refs=[],
            approval_refs=[],
        ),
        governed_trace(
            id="trace-2042-decision",
            agent_run_id="RUN-2042",
            sequence=5,
            category="decision.refund_eligibility",
            risk="Medium",
            label="Evaluated duplicate-charge refund eligibility",
            input_summary="Compared captured charges, invoice total, policy, and prior actions.",
            output_summary=(
                "Refund the duplicate captured charge ch_2026_0418_B to the original payment "
                "method after human approval."
            ),
            evidence_refs=[
                "invoice INV-2026-0418",
                "charge ch_2026_0418_A",
                "charge ch_2026_0418_B",
                "policy REFUND-DUP-001 v2026.02",
            ],
            policy_refs=["REFUND-DUP-001 v2026.02"],
            approval_refs=[],
        ),
        governed_trace(
            id="trace-2042-draft",
            agent_run_id="RUN-2042",
            sequence=6,
            category="draft.resolution",
            risk="Low",
            label="Drafted governed resolution",
            input_summary="Prepared internal and customer-facing draft output.",
            output_summary=(
                "Draft-only resolution text was stored without sending a customer reply."
            ),
            evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
            policy_refs=["REFUND-DUP-001 v2026.02"],
            approval_refs=[],
        ),
        governed_trace(
            id="trace-2042-approval",
            agent_run_id="RUN-2042",
            sequence=7,
            category="approval.create_request",
            risk="Medium",
            label="Created approval request for financial action",
            input_summary="Created human approval gate for proposed original refund.",
            output_summary="Approval request APR-2042 is pending.",
            evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
            policy_refs=["REFUND-DUP-001 v2026.02"],
            approval_refs=["APR-2042"],
        ),
    ],
    "RUN-1137": [
        governed_trace(
            id="trace-1137-plan",
            agent_run_id="RUN-1137",
            sequence=1,
            category="plan.investigation",
            risk="Low",
            label="LLM proposed investigation tool plan",
            input_summary=(
                "Requested investigation plan for TCK-1137 before reading billing evidence."
            ),
            output_summary="Investigate credit/refund evidence and backend eligibility.",
            evidence_refs=["ticket TCK-1137"],
            policy_refs=[],
            approval_refs=[],
            governance_metadata_extra=plan_investigation_metadata(
                plan_summary="Investigate credit/refund evidence and backend eligibility.",
                steps=[
                    {
                        "step_id": "evidence",
                        "action_id": "read.credit_refund_evidence",
                        "evidence_targets": [
                            "account_state",
                            "invoice",
                            "charges",
                            "payment_status",
                            "credit_ledger",
                            "subscription",
                            "policy",
                        ],
                        "rationale": (
                            "Read credit ledger, subscription, invoice, charge, and "
                            "policy evidence."
                        ),
                        "depends_on": [],
                    },
                    {
                        "step_id": "prior",
                        "action_id": "read.prior_financial_actions",
                        "evidence_targets": ["prior_financial_actions"],
                        "rationale": (
                            "Check prior financial actions to avoid duplicate credits or refunds."
                        ),
                        "depends_on": [],
                    },
                    {
                        "step_id": "decision",
                        "action_id": "decision.credit_refund_eligibility",
                        "evidence_targets": [
                            "invoice",
                            "charges",
                            "credit_ledger",
                            "subscription",
                            "policy",
                            "prior_financial_actions",
                        ],
                        "rationale": (
                            "Ask the backend decision tool to classify credit/refund eligibility."
                        ),
                        "depends_on": ["evidence", "prior"],
                    },
                ],
            ),
        ),
        governed_trace(
            id="trace-1137-plan-verify",
            agent_run_id="RUN-1137",
            sequence=2,
            category="plan.verify",
            risk="Low",
            label="Backend verified investigation plan contract",
            input_summary=(
                "Checked planned actions, evidence targets, dependencies, and safety scope."
            ),
            output_summary="Plan verifier accepted the investigation plan.",
            evidence_refs=["ticket TCK-1137"],
            policy_refs=[],
            approval_refs=[],
            governance_metadata_extra=plan_verify_metadata(
                normalized_action_ids=[
                    "read.credit_refund_evidence",
                    "read.prior_financial_actions",
                    "decision.credit_refund_eligibility",
                ],
                required_targets_seen=[
                    "account_state",
                    "invoice",
                    "charges",
                    "payment_status",
                    "credit_ledger",
                    "subscription",
                    "policy",
                    "prior_financial_actions",
                ],
            ),
        ),
        governed_trace(
            id="trace-1137-read-evidence",
            agent_run_id="RUN-1137",
            sequence=3,
            category="read.credit_refund_evidence",
            risk="Low",
            label="Collected Credit/Refund dispute evidence",
            input_summary=(
                "Read ticket, subscription, invoice, charges, credit ledger, and policy for "
                "TCK-1137."
            ),
            output_summary=(
                "Found invoice INV-2026-0312, 1 credit ledger entry, and 3 policy citations."
            ),
            evidence_refs=[
                "invoice INV-2026-0312",
                "charge ch_2026_0312_A",
                "credit cred-ledger-1137",
                "subscription sub-helio-2026",
            ],
            policy_refs=[
                "TRIAL-CREDIT-003 v2026.03",
                "CANCEL-REFUND-004 v2026.03",
                "ADJUSTMENT-LIMIT-002 v2026.03",
            ],
            approval_refs=[],
        ),
        governed_trace(
            id="trace-1137-prior-actions",
            agent_run_id="RUN-1137",
            sequence=4,
            category="read.prior_financial_actions",
            risk="Low",
            label="Checked prior approvals and mock mutations",
            input_summary="Read existing approval and mutation state for TCK-1137.",
            output_summary="Found 0 executed mock financial action(s).",
            evidence_refs=["ticket TCK-1137"],
            policy_refs=[],
            approval_refs=[],
        ),
        governed_trace(
            id="trace-1137-decision",
            agent_run_id="RUN-1137",
            sequence=5,
            category="decision.credit_refund_eligibility",
            risk="Medium",
            label="Evaluated credit/refund eligibility",
            input_summary=(
                "Compared credit ledger, cancellation timing, invoice, and prior actions."
            ),
            output_summary=(
                "Create a goodwill credit for the disputed remaining trial credit $120.00 after "
                "human approval."
            ),
            evidence_refs=[
                "credit cred-ledger-1137",
                "subscription sub-helio-2026",
                "invoice INV-2026-0312",
                "policy TRIAL-CREDIT-003 v2026.03",
            ],
            policy_refs=["TRIAL-CREDIT-003 v2026.03"],
            approval_refs=[],
        ),
        governed_trace(
            id="trace-1137-draft",
            agent_run_id="RUN-1137",
            sequence=6,
            category="draft.resolution",
            risk="Low",
            label="Drafted governed resolution",
            input_summary="Prepared internal and customer-facing draft output.",
            output_summary=(
                "Draft-only resolution text was stored without sending a customer reply."
            ),
            evidence_refs=["invoice INV-2026-0312", "credit cred-ledger-1137"],
            policy_refs=["TRIAL-CREDIT-003 v2026.03"],
            approval_refs=[],
        ),
        governed_trace(
            id="trace-1137-approval",
            agent_run_id="RUN-1137",
            sequence=7,
            category="approval.create_request",
            risk="Medium",
            label="Created approval request for financial action",
            input_summary="Created human approval gate for proposed goodwill credit.",
            output_summary="Approval request APR-1137 is pending.",
            evidence_refs=[
                "credit cred-ledger-1137",
                "subscription sub-helio-2026",
                "invoice INV-2026-0312",
            ],
            policy_refs=["TRIAL-CREDIT-003 v2026.03"],
            approval_refs=["APR-1137"],
        ),
    ],
}

APPROVALS: list[ApprovalSummary] = [
    ApprovalSummary(
        id="APR-2042",
        ticket_id="TCK-1042",
        agent_run_id="RUN-2042",
        title="Original refund pending approval",
        status="pending",
        action_type="original_refund",
        amount=money(124800),
        reason=(
            "Refund the duplicate captured charge ch_2026_0418_B to the original payment method."
        ),
        policy_citation="REFUND-DUP-001 v2026.02",
        blocker="Mutation blocked until human approval",
        evidence_refs=["invoice INV-2026-0418", "charge ch_2026_0418_B"],
        action_metadata={
            "action_type": "original_refund",
            "invoice_id": "INV-2026-0418",
            "target_charge_id": "ch_2026_0418_B",
            "action_basis": "confirmed_duplicate_charge",
        },
        action_fingerprint=build_action_fingerprint(
            ticket_id="TCK-1042",
            action_type="original_refund",
            amount_cents=124800,
            currency="USD",
            action_metadata={
                "target_charge_id": "ch_2026_0418_B",
                "invoice_id": "INV-2026-0418",
            },
        ),
    ),
    ApprovalSummary(
        id="APR-1137",
        ticket_id="TCK-1137",
        agent_run_id="RUN-1137",
        title="Goodwill credit pending approval",
        status="pending",
        action_type="goodwill_credit",
        amount=money(12000),
        reason=(
            "Create a goodwill credit for the disputed remaining trial credit $120.00 after "
            "human approval."
        ),
        policy_citation="TRIAL-CREDIT-003 v2026.03",
        blocker="Mutation blocked until human approval",
        evidence_refs=[
            "credit cred-ledger-1137",
            "subscription sub-helio-2026",
            "invoice INV-2026-0312",
        ],
        action_metadata={
            "action_type": "goodwill_credit",
            "credit_ledger_entry_id": "cred-ledger-1137",
            "subscription_id": "sub-helio-2026",
            "action_basis": "goodwill_credit_requires_approval",
        },
        action_fingerprint=build_action_fingerprint(
            ticket_id="TCK-1137",
            action_type="goodwill_credit",
            amount_cents=12000,
            currency="USD",
            action_metadata={"credit_ledger_entry_id": "cred-ledger-1137"},
        ),
    ),
    ApprovalSummary(
        id="APR-EVAL-CR-003-HIST",
        ticket_id="EVAL-TCK-CR-003",
        agent_run_id=None,
        title="Historical goodwill credit approved",
        status="approved",
        action_type="goodwill_credit",
        amount=money(12000),
        reason="Historical goodwill credit already resolved this trial credit dispute.",
        policy_citation="ADJUSTMENT-LIMIT-002 v2026.03",
        blocker="Approved historical mock mutation",
        evidence_refs=[
            "credit cred-ledger-eval-cr-003",
            "subscription sub-eval-cr-003",
        ],
        action_metadata={
            "action_type": "goodwill_credit",
            "credit_ledger_entry_id": "cred-ledger-eval-cr-003",
            "subscription_id": "sub-eval-cr-003",
            "action_basis": "goodwill_credit_requires_approval",
        },
        action_fingerprint=build_action_fingerprint(
            ticket_id="EVAL-TCK-CR-003",
            action_type="goodwill_credit",
            amount_cents=12000,
            currency="USD",
            action_metadata={"credit_ledger_entry_id": "cred-ledger-eval-cr-003"},
        ),
        decided_at=utc(2026, 5, 28, 15, 44),
        decision="approved",
        decided_by="Demo Operator",
        decision_note="Historical seeded approval.",
    ),
]

MOCK_MUTATIONS = [
    MockMutationSummary(
        id="MM-EVAL-CR-003-HIST",
        ticket_id="EVAL-TCK-CR-003",
        approval_request_id="APR-EVAL-CR-003-HIST",
        agent_run_id=None,
        mutation_type="goodwill_credit",
        status="mock_executed",
        amount=money(12000),
        reason="Historical goodwill credit already resolved this trial credit dispute.",
        action_metadata={
            "action_type": "goodwill_credit",
            "credit_ledger_entry_id": "cred-ledger-eval-cr-003",
            "subscription_id": "sub-eval-cr-003",
        },
        action_fingerprint=build_action_fingerprint(
            ticket_id="EVAL-TCK-CR-003",
            action_type="goodwill_credit",
            amount_cents=12000,
            currency="USD",
            action_metadata={"credit_ledger_entry_id": "cred-ledger-eval-cr-003"},
        ),
        executed_at=utc(2026, 5, 28, 15, 45),
        executed_at_display="May 28, 2026 15:45 UTC",
    )
]

EVAL_CASES = [
    EvalCaseSummary(
        id="eval-duplicate-charge-001",
        scenario="duplicate_charge",
        title="Duplicate Charge golden path",
        description="Same invoice has two captured charges for the exact invoice total.",
        expected_outcome="confirmed_duplicate_charge",
        required_evidence=["invoice", "charges", "credit_ledger", "usage", "policy"],
        policy_refs=["REFUND-DUP-001 v2026.02"],
        expected_approval_routing="refund_requires_approval",
        fixture_ticket_id="EVAL-TCK-DUP-001",
    ),
    EvalCaseSummary(
        id="eval-duplicate-charge-002",
        scenario="duplicate_charge",
        title="Duplicate authorization not captured",
        description="Second payment event is an authorization that never captured.",
        expected_outcome="no_refund_expected_billing_behavior",
        required_evidence=["invoice", "charges", "payment_status", "policy"],
        policy_refs=["REFUND-DUP-001 v2026.02"],
        expected_approval_routing="no_financial_action",
        fixture_ticket_id="EVAL-TCK-DUP-002",
    ),
    EvalCaseSummary(
        id="eval-duplicate-charge-003",
        scenario="duplicate_charge",
        title="Insufficient duplicate evidence",
        description="Customer reports duplicate payment but only one captured charge is linked.",
        expected_outcome="insufficient_evidence_human_review",
        required_evidence=["invoice", "charges", "account_state", "policy"],
        policy_refs=["REFUND-DUP-001 v2026.02"],
        expected_approval_routing="no_mutation_without_evidence",
        fixture_ticket_id="EVAL-TCK-DUP-003",
    ),
    EvalCaseSummary(
        id="eval-usage-spike-001",
        scenario="usage_spike",
        title="Customer batch import spike",
        description="Valid API key usage spike caused a larger invoice.",
        expected_outcome="expected_usage_no_refund",
        required_evidence=["usage", "invoice", "pricing", "policy"],
        policy_refs=["USAGE-SPIKE-002 v2026.01"],
        expected_approval_routing="goodwill_credit_requires_approval",
    ),
    EvalCaseSummary(
        id="eval-usage-spike-002",
        scenario="usage_spike",
        title="Unexpected usage with alert gap",
        description="Usage spike occurred after alert threshold configuration was changed.",
        expected_outcome="human_review_possible_goodwill_credit",
        required_evidence=["usage", "account_state", "alert_config", "policy"],
        policy_refs=["USAGE-SPIKE-002 v2026.01"],
        expected_approval_routing="credit_requires_approval",
    ),
    EvalCaseSummary(
        id="eval-usage-spike-003",
        scenario="usage_spike",
        title="Usage spike missing logs",
        description="Usage invoice is high but detailed metering evidence is unavailable.",
        expected_outcome="insufficient_evidence_human_review",
        required_evidence=["invoice", "usage", "policy"],
        policy_refs=["USAGE-SPIKE-002 v2026.01"],
        expected_approval_routing="no_mutation_without_evidence",
    ),
    EvalCaseSummary(
        id="eval-credit-refund-001",
        scenario="credit_refund_dispute",
        title="Trial credit consumed before cancellation",
        description="Credit was consumed before cancellation but customer requests reinstatement.",
        expected_outcome="goodwill_credit_requires_approval",
        required_evidence=["credit_ledger", "subscription", "invoice", "policy"],
        policy_refs=["TRIAL-CREDIT-003 v2026.03"],
        expected_approval_routing="credit_requires_approval",
        fixture_ticket_id="EVAL-TCK-CR-001",
    ),
    EvalCaseSummary(
        id="eval-credit-refund-002",
        scenario="credit_refund_dispute",
        title="Cancellation before renewal capture",
        description="Customer canceled before the renewal charge should have captured.",
        expected_outcome="refund_requires_approval",
        required_evidence=["subscription", "invoice", "charges", "policy"],
        policy_refs=["CANCEL-REFUND-004 v2026.03"],
        expected_approval_routing="refund_requires_approval",
        fixture_ticket_id="EVAL-TCK-CR-002",
    ),
    EvalCaseSummary(
        id="eval-credit-refund-003",
        scenario="credit_refund_dispute",
        title="Prior adjustment already granted",
        description=(
            "Customer disputes a charge after a prior credit adjustment was already applied."
        ),
        expected_outcome="prior_adjustment_already_applied",
        required_evidence=["credit_ledger", "prior_adjustment", "invoice", "policy"],
        policy_refs=["ADJUSTMENT-LIMIT-002 v2026.03"],
        expected_approval_routing="no_duplicate_mutation",
        fixture_ticket_id="EVAL-TCK-CR-003",
    ),
]

EVAL_RESULTS: list[EvalResultSummary] = []

EVAL_RUNS = [
    EvalRunSummary(
        id=BASELINE_RUN_ID,
        run_type="baseline",
        status="completed",
        summary="Seeded canonical baseline for M10 eval regression comparison.",
        baseline_name=BASELINE_NAME,
        case_id=None,
        started_at=utc(2026, 6, 30, 0, 0),
        completed_at=utc(2026, 6, 30, 0, 1),
    )
]


def build_seed_repository() -> InMemoryMeterDeskRepository:
    return InMemoryMeterDeskRepository(
        tickets=TICKETS,
        ticket_details={**TICKET_DETAILS, **EVAL_TICKET_DETAILS},
        billing_evidence={**BILLING_EVIDENCE, **EVAL_BILLING_EVIDENCE},
        agent_runs=AGENT_RUNS,
        traces=TRACES,
        approvals=APPROVALS,
        mock_mutations=MOCK_MUTATIONS,
        eval_cases=EVAL_CASES,
        eval_results=EVAL_RESULTS,
        eval_runs=EVAL_RUNS,
        eval_result_snapshots=[_baseline_snapshot_for_case(eval_case) for eval_case in EVAL_CASES],
    )


def _baseline_snapshot_for_case(eval_case: EvalCaseSummary) -> EvalResultSnapshotSummary:
    is_usage_gap = eval_case.scenario == "usage_spike"
    status = "blocked" if is_usage_gap else "passed"
    result_id = f"EVAL-BASELINE-{eval_case.id}"
    dimension_scores = {
        dimension: ("not_run" if dimension == "draft_quality" else "blocked")
        if is_usage_gap
        else ("not_run" if dimension == "draft_quality" else "pass")
        for dimension in DIMENSION_NAMES
    }
    blocked_details = {
        "blocked_reason": "Scenario runner is not implemented for this scenario",
        "blocked_code": "scenario.runner_not_implemented",
        "readiness_gaps": [
            "usage window and baseline evidence model",
            "meter dimensions and pricing evidence model",
            "usage spike deterministic decision tool",
            "goodwill credit governed action fixtures",
        ],
    }
    details = {
        "failed_checks": [],
        "missing_evidence": eval_case.required_evidence if is_usage_gap else [],
        "policy_refs_seen": [] if is_usage_gap else eval_case.policy_refs,
        "trace_refs": [],
        "judge_notes": [],
        "model": None if is_usage_gap else "seeded-demo",
        "prompt_version": None if is_usage_gap else _prompt_version_for_case(eval_case),
        **(blocked_details if is_usage_gap else {"blocked_reason": None}),
    }
    return EvalResultSnapshotSummary(
        id=f"EVS-BASELINE-{eval_case.id}",
        eval_run_id=BASELINE_RUN_ID,
        result_id=result_id,
        case_id=eval_case.id,
        agent_run_id=None,
        snapshot_type="baseline",
        status=status,
        summary=(
            "Scenario runner is not implemented for this scenario"
            if is_usage_gap
            else "Seeded deterministic baseline checks passed."
        ),
        dimension_scores=dimension_scores,
        details=details,
        trace_signature=_baseline_trace_signature(eval_case),
        version_snapshot={
            "model": None if is_usage_gap else "seeded-demo",
            "prompt_version": None if is_usage_gap else _prompt_version_for_case(eval_case),
            "prompt_fingerprint": build_prompt_fingerprint(),
            "policy_refs_seen": [] if is_usage_gap else eval_case.policy_refs,
            "tool_policy_versions": {
                category: "1.0.0"
                for category in _baseline_trace_signature(eval_case)["ordered_categories"]
            },
            "governance_schema_version": "1.0.0",
            "grader_version": GRADER_VERSION,
            "result_schema_version": RESULT_SCHEMA_VERSION,
        },
        explanations=(
            ["Scenario runner is not implemented for this scenario; tracked as a coverage gap."]
            if is_usage_gap
            else ["Seeded baseline deterministic checks passed."]
        ),
        created_at=utc(2026, 6, 30, 0, 1),
    )


def _prompt_version_for_case(eval_case: EvalCaseSummary) -> str:
    if eval_case.scenario == "credit_refund_dispute":
        return "m8-credit-refund-v1"
    return "m3-duplicate-charge-v1"


def _baseline_trace_signature(eval_case: EvalCaseSummary) -> dict[str, object]:
    if eval_case.scenario == "usage_spike":
        return {
            "ordered_categories": [],
            "evidence_categories": [],
            "policy_refs": [],
            "approval_refs": [],
            "governance_reason_codes": [],
        }
    read_action = (
        "read.credit_refund_evidence"
        if eval_case.scenario == "credit_refund_dispute"
        else "read.billing_evidence"
    )
    decision_action = (
        "decision.credit_refund_eligibility"
        if eval_case.scenario == "credit_refund_dispute"
        else "decision.refund_eligibility"
    )
    categories = [
        "plan.investigation",
        "plan.verify",
        read_action,
        "read.prior_financial_actions",
        decision_action,
        "draft.resolution",
    ]
    if "requires_approval" in eval_case.expected_approval_routing:
        categories.append("approval.create_request")
    return {
        "ordered_categories": categories,
        "evidence_categories": eval_case.required_evidence,
        "policy_refs": eval_case.policy_refs,
        "approval_refs": ["approval_request"]
        if "requires_approval" in eval_case.expected_approval_routing
        else [],
        "governance_reason_codes": ["governance.allowed"],
    }


EVAL_RESULT_SNAPSHOTS = [
    _baseline_snapshot_for_case(eval_case) for eval_case in EVAL_CASES
]
