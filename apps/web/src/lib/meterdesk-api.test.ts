import { afterEach, describe, expect, it, vi } from "vitest";

import { MeterDeskApiError, startAgentRun } from "./meterdesk-api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("meterdesk-api", () => {
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
