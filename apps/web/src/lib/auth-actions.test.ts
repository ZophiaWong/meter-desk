import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  redirect: vi.fn((destination: string) => {
    throw new Error(`REDIRECT:${destination}`);
  }),
}));

vi.mock("@/lib/meterdesk-api", () => ({
  demoLogin: vi.fn(),
}));

vi.mock("@/lib/session", () => ({
  clearDemoSessionCookie: vi.fn(),
  setDemoSessionCookie: vi.fn(),
}));

import { redirect } from "next/navigation";

import { demoLogin } from "@/lib/meterdesk-api";
import { clearDemoSessionCookie, setDemoSessionCookie } from "@/lib/session";
import { loginAction, logoutAction, switchIdentityAction } from "./auth-actions";

const loginResponse = {
  access_token: "signed-jwt",
  token_type: "bearer" as const,
  expires_in: 28_800,
  principal: {
    subject: "demo-approver",
    display_name: "Demo Approver",
    role: "approver" as const,
  },
};

describe("demo auth actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(demoLogin).mockResolvedValue(loginResponse);
  });

  it("logs in a fixed identity, stores its JWT, and redirects to a safe relative returnTo", async () => {
    const formData = new FormData();
    formData.set("subject", "demo-approver");
    formData.set("returnTo", "/approvals?status=pending");

    await expect(loginAction(formData)).rejects.toThrow(
      "REDIRECT:/approvals?status=pending",
    );
    expect(demoLogin).toHaveBeenCalledWith("demo-approver");
    expect(setDemoSessionCookie).toHaveBeenCalledWith("signed-jwt", 28_800);
  });

  it("does not allow an external returnTo during identity switching", async () => {
    const formData = new FormData();
    formData.set("subject", "demo-approver");
    formData.set("returnTo", "https://evil.example/phish");

    await expect(switchIdentityAction(formData)).rejects.toThrow("REDIRECT:/");
    expect(setDemoSessionCookie).toHaveBeenCalledWith("signed-jwt", 28_800);
  });

  it("clears the shared cookie on logout", async () => {
    await expect(logoutAction()).rejects.toThrow("REDIRECT:/login");

    expect(clearDemoSessionCookie).toHaveBeenCalledTimes(1);
    expect(redirect).toHaveBeenCalledWith("/login");
  });

  it("rejects a form without a demo subject before calling FastAPI", async () => {
    await expect(loginAction(new FormData())).rejects.toThrow("subject is required");

    expect(demoLogin).not.toHaveBeenCalled();
    expect(setDemoSessionCookie).not.toHaveBeenCalled();
  });
});
