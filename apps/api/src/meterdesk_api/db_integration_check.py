import asyncio

from httpx import ASGITransport, AsyncClient

from meterdesk_api.agent.runtime import get_agent_provider
from meterdesk_api.errors import MeterDeskAPIError
from meterdesk_api.main import app


async def authenticate(client: AsyncClient, subject: str) -> None:
    response = await client.post("/auth/demo-login", json={"subject": subject})
    response.raise_for_status()
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


async def run_db_integration_check() -> None:
    async def missing_provider_override():
        raise MeterDeskAPIError(
            status_code=503,
            code="provider.not_configured",
            message="OpenAI-compatible provider is not configured.",
        )

    app.dependency_overrides[get_agent_provider] = missing_provider_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            anonymous_tickets = await client.get("/tickets")
            await authenticate(client, "demo-support-operator")
            tickets = await client.get("/tickets")
            evidence = await client.get("/tickets/TCK-1042/billing-evidence")
            credit_refund_evidence = await client.get("/tickets/TCK-1137/billing-evidence")
            approvals = await client.get("/approvals")
            runs = await client.get("/tickets/TCK-1042/agent-runs")
            credit_refund_runs = await client.get("/tickets/TCK-1137/agent-runs")
            eval_cases = await client.get("/eval-cases")
            write = await client.post("/tickets/TCK-1042/agent-runs")
            operator_approval = await client.post("/approvals/APR-2042/approve", json={})

            await authenticate(client, "demo-approver")
            decision = await client.post(
                "/approvals/APR-2042/approve",
                json={"decision_note": "Approved by the database integration check."},
            )
            mutations = await client.get("/mock-mutations?ticket_id=TCK-1042")
            credit_mutations_before = await client.get("/mock-mutations?ticket_id=TCK-1137")
            rejection = await client.post(
                "/approvals/APR-1137/reject",
                json={"decision_note": "Rejected by the database integration check."},
            )
            credit_mutations_after = await client.get("/mock-mutations?ticket_id=TCK-1137")
            historical_approval = await client.get(
                "/approvals?ticket_id=EVAL-TCK-CR-003&status=all"
            )

            await authenticate(client, "demo-admin")
            retry = await client.post(
                "/approvals/APR-2042/approve",
                json={"decision_note": "This retry must not replace the approver audit."},
            )
            mutations_after_retry = await client.get("/mock-mutations?ticket_id=TCK-1042")
    finally:
        app.dependency_overrides.pop(get_agent_provider, None)

    assert anonymous_tickets.status_code == 401
    assert tickets.status_code == 200
    assert [ticket["id"] for ticket in tickets.json()] == ["TCK-1042", "TCK-1098", "TCK-1137"]
    assert evidence.status_code == 200
    assert evidence.json()["invoice"]["id"] == "INV-2026-0418"
    assert credit_refund_evidence.status_code == 200
    assert credit_refund_evidence.json()["subscription"]["id"] == "sub-helio-2026"
    assert credit_refund_evidence.json()["credits"][0]["disputed_amount"]["display"] == "$120.00"
    assert approvals.status_code == 200
    assert [approval["id"] for approval in approvals.json()] == ["APR-2042", "APR-1137"]
    assert runs.status_code == 200
    assert [run["id"] for run in runs.json()] == ["RUN-2042"]
    assert credit_refund_runs.status_code == 200
    assert [run["id"] for run in credit_refund_runs.json()] == ["RUN-1137"]
    assert eval_cases.status_code == 200
    assert len(eval_cases.json()) == 9
    assert write.status_code == 503
    assert write.json()["code"] == "provider.not_configured"
    assert operator_approval.status_code == 403
    assert operator_approval.json()["code"] == "auth.forbidden"

    assert decision.status_code == 200
    decided_approval = decision.json()["approval"]
    assert decided_approval["decision_actor"] == {
        "subject": "demo-approver",
        "display_name": "Demo Approver",
        "role": "approver",
        "source": "demo_session",
    }
    assert decided_approval["decision_request_id"] == decision.headers["X-Request-ID"]
    assert len(mutations.json()) == 1
    assert mutations.json()[0]["approval_request_id"] == "APR-2042"

    assert rejection.status_code == 200
    rejected_approval = rejection.json()["approval"]
    assert rejected_approval["status"] == "rejected"
    assert rejected_approval["decision_actor"]["subject"] == "demo-approver"
    assert rejected_approval["decision_request_id"] == rejection.headers["X-Request-ID"]
    assert credit_mutations_after.json() == credit_mutations_before.json()

    seeded_actor = historical_approval.json()[0]
    assert seeded_actor["decision_actor"]["subject"] == "demo-approver"
    assert seeded_actor["decision_actor"]["source"] == "seed_fixture"
    assert seeded_actor["decision_request_id"] == "req_seed_eval_cr_003_hist"

    assert retry.status_code == 200
    assert retry.json()["approval"] == decided_approval
    assert retry.json()["mock_mutation"]["id"] == decision.json()["mock_mutation"]["id"]
    assert len(mutations_after_retry.json()) == 1

    print("MeterDesk P0-02 DB integration check passed.")


def main() -> None:
    asyncio.run(run_db_integration_check())


if __name__ == "__main__":
    main()
