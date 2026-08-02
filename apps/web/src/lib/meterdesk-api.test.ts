import { afterEach, describe, expect, it, vi } from "vitest";

import {
  approveRequest,
  demoLogin,
  getCurrentDemoPrincipal,
  getDecisionSummary,
  getDemoIdentities,
  MeterDeskApiError,
  startAgentRun,
} from "./meterdesk-api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("meterdesk-api", () => {
  it("uses the public demo auth endpoints and verifies the returned token via /auth/me", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              subject: "demo-approver",
              display_name: "Demo Approver",
              role: "approver",
            },
          ]),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "signed-jwt",
            token_type: "bearer",
            expires_in: 28_800,
            principal: {
              subject: "demo-approver",
              display_name: "Demo Approver",
              role: "approver",
            },
          }),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            subject: "demo-approver",
            display_name: "Demo Approver",
            role: "approver",
          }),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchSpy);

    const identities = await getDemoIdentities("http://api.test");
    const login = await demoLogin("demo-approver", "http://api.test");
    const principal = await getCurrentDemoPrincipal("signed-jwt", "http://api.test");

    expect(identities[0]?.subject).toBe("demo-approver");
    expect(login.expires_in).toBe(28_800);
    expect(principal.role).toBe("approver");
    expect(fetchSpy).toHaveBeenNthCalledWith(1, "http://api.test/auth/demo-identities", {
      cache: "no-store",
    });
    expect(fetchSpy).toHaveBeenNthCalledWith(2, "http://api.test/auth/demo-login", {
      body: JSON.stringify({ subject: "demo-approver" }),
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    expect(fetchSpy).toHaveBeenNthCalledWith(3, "http://api.test/auth/me", {
      cache: "no-store",
      headers: { Authorization: "Bearer signed-jwt" },
    });
  });

  it("fetches the agent decision summary for a ticket", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          ticket_id: "TCK-1042",
          state: "pending_approval",
          decision_label: "Duplicate captured charge confirmed",
          rationale:
            "Agent confirmed a duplicate captured charge on INV-2026-0418; mutation remains blocked until human approval.",
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
              body: "The governed decision tool classified the duplicate charge.",
              tone: "success",
              refs: ["RUN-2042"],
            },
            {
              kind: "evidence",
              label: "Evidence",
              title: "Invoice and duplicate charge evidence",
              body: "INV-2026-0418 has two captured charges.",
              tone: "info",
              refs: ["INV-2026-0418", "ch_2026_0418_A", "ch_2026_0418_B"],
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
        }),
        {
          headers: { "Content-Type": "application/json" },
          status: 200,
        },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    const summary = await getDecisionSummary("TCK-1042", "http://api.test", "session-token");

    expect(fetchSpy).toHaveBeenCalledWith("http://api.test/tickets/TCK-1042/decision-summary", {
      cache: "no-store",
      headers: { Authorization: "Bearer session-token" },
    });
    expect(summary.state).toBe("pending_approval");
    expect(summary.tiles.map((tile) => tile.kind)).toEqual([
      "decision",
      "evidence",
      "risk_gate",
      "draft",
    ]);
  });

  it("forwards bearer auth without allowing an approval actor in the request body", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify({ approval: {}, mock_mutation: null }), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    await approveRequest("APR-2042", "http://api.test", "approver-token");

    expect(fetchSpy).toHaveBeenCalledWith("http://api.test/approvals/APR-2042/approve", {
      body: "{}",
      cache: "no-store",
      headers: {
        Authorization: "Bearer approver-token",
        "Content-Type": "application/json",
      },
      method: "POST",
    });
  });

  it("preserves structured API error codes and details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            code: "approval.pending_duplicate",
            message: "A pending financial approval already exists for this action.",
            details: {
              action_fingerprint:
                "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD",
            },
          }),
          {
            headers: { "Content-Type": "application/json" },
            status: 409,
          },
        ),
      ),
    );

    await expect(startAgentRun("TCK-1042")).rejects.toMatchObject({
      code: "approval.pending_duplicate",
      details: {
        action_fingerprint:
          "ticket:TCK-1042|action:original_refund|target:ch_2026_0418_B|amount:124800|currency:USD",
      },
      message: "A pending financial approval already exists for this action.",
      status: 409,
    });
  });

  it("falls back to a generic message for non-structured API errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 500 })));

    await expect(startAgentRun("TCK-1042")).rejects.toBeInstanceOf(MeterDeskApiError);
    await expect(startAgentRun("TCK-1042")).rejects.toMatchObject({
      code: "api.request_failed",
      message: "FastAPI request failed for /tickets/TCK-1042/agent-runs",
      status: 500,
    });
  });
});
