import { describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

vi.mock("@/lib/meterdesk-api", () => ({
  approveRequest: vi.fn(),
  rejectRequest: vi.fn(),
  runAllEvalCases: vi.fn(),
  runEvalCase: vi.fn(),
  startAgentRun: vi.fn(),
}));

import { revalidatePath } from "next/cache";

import { startAgentRunAction } from "./meterdesk-actions";
import { startAgentRun } from "@/lib/meterdesk-api";

describe("meterdesk-actions", () => {
  it("starts an agent run for the selected Workbench ticket", async () => {
    const formData = new FormData();
    formData.set("ticketId", "TCK-1137");

    await startAgentRunAction(formData);

    expect(startAgentRun).toHaveBeenCalledWith("TCK-1137");
    expect(revalidatePath).toHaveBeenCalledWith("/");
    expect(revalidatePath).toHaveBeenCalledWith("/?ticket=TCK-1137");
    expect(revalidatePath).toHaveBeenCalledWith("/approvals");
  });
});
