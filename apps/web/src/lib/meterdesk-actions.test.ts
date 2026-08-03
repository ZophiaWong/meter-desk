import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn((destination: string) => {
    throw new Error(`REDIRECT:${destination}`);
  }),
}));

vi.mock("@/lib/meterdesk-api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/meterdesk-api")>();
  return {
    ...actual,
    approveRequest: vi.fn(),
    rejectRequest: vi.fn(),
    runAllEvalCases: vi.fn(),
    runEvalCase: vi.fn(),
    startAgentRun: vi.fn(),
  };
});

vi.mock("@/lib/session", () => ({
  clearDemoSessionCookie: vi.fn(),
  requireDemoSession: vi.fn(),
}));

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { approveRequestAction, startAgentRunAction } from "./meterdesk-actions";
import { approveRequest, MeterDeskApiError, startAgentRun } from "@/lib/meterdesk-api";
import { clearDemoSessionCookie, requireDemoSession } from "@/lib/session";

const adminSession = {
  accessToken: "admin-token",
  principal: {
    subject: "demo-admin",
    display_name: "Demo Admin",
    role: "admin" as const,
  },
};

describe("meterdesk-actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(requireDemoSession).mockResolvedValue(adminSession);
  });

  it("starts an agent run for the selected Workbench ticket", async () => {
    const formData = new FormData();
    formData.set("ticketId", "TCK-1137");

    await startAgentRunAction(formData);

    expect(requireDemoSession).toHaveBeenCalledWith("/?ticket=TCK-1137");
    expect(startAgentRun).toHaveBeenCalledWith("TCK-1137", undefined, "admin-token");
    expect(revalidatePath).toHaveBeenCalledWith("/");
    expect(revalidatePath).toHaveBeenCalledWith("/?ticket=TCK-1137");
    expect(revalidatePath).toHaveBeenCalledWith("/approvals");
  });

  it("clears a stale cookie and returns to login when FastAPI rejects the token", async () => {
    vi.mocked(startAgentRun).mockRejectedValue(
      new MeterDeskApiError("Invalid token", 401, "auth.invalid_token"),
    );
    const formData = new FormData();
    formData.set("ticketId", "TCK-1137");

    await expect(startAgentRunAction(formData)).rejects.toThrow(
      "REDIRECT:/login?reason=session-expired&returnTo=%2F%3Fticket%3DTCK-1137",
    );
    expect(clearDemoSessionCookie).toHaveBeenCalledTimes(1);
  });

  it("keeps the identity and shows a forbidden explanation for insufficient approval role", async () => {
    vi.mocked(approveRequest).mockRejectedValue(
      new MeterDeskApiError("Forbidden", 403, "auth.forbidden", {}, "req_denied"),
    );
    const formData = new FormData();
    formData.set("approvalId", "APR-2042");

    await expect(approveRequestAction(formData)).rejects.toThrow(
      "REDIRECT:/forbidden?returnTo=%2Fapprovals&requestId=req_denied",
    );
    expect(clearDemoSessionCookie).not.toHaveBeenCalled();
    expect(redirect).toHaveBeenCalledTimes(1);
  });
});
