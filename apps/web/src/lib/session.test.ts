import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieStore = {
  delete: vi.fn(),
  get: vi.fn(),
  set: vi.fn(),
};
const headerStore = {
  get: vi.fn(),
};

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => cookieStore),
  headers: vi.fn(async () => headerStore),
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
    getCurrentDemoPrincipal: vi.fn(),
  };
});

import { redirect } from "next/navigation";

import { getCurrentDemoPrincipal, MeterDeskApiError } from "@/lib/meterdesk-api";
import {
  clearDemoSessionCookie,
  DEMO_SESSION_COOKIE,
  requireDemoSession,
  setDemoSessionCookie,
} from "./session";

const approver = {
  subject: "demo-approver",
  display_name: "Demo Approver",
  role: "approver" as const,
};

describe("demo session DAL", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    cookieStore.get.mockReturnValue(undefined);
    headerStore.get.mockReturnValue(null);
  });

  it("stores the JWT only in an eight-hour HttpOnly cookie and enables Secure for HTTPS", async () => {
    headerStore.get.mockImplementation((name: string) =>
      name === "x-forwarded-proto" ? "https" : null,
    );

    await setDemoSessionCookie("signed-jwt");

    expect(cookieStore.set).toHaveBeenCalledWith(DEMO_SESSION_COOKIE, "signed-jwt", {
      httpOnly: true,
      maxAge: 28_800,
      path: "/",
      sameSite: "lax",
      secure: true,
    });
  });

  it("omits Secure for a local HTTP demo", async () => {
    headerStore.get.mockImplementation((name: string) =>
      name === "origin" ? "http://localhost:3000" : null,
    );

    await setDemoSessionCookie("signed-jwt");

    expect(cookieStore.set).toHaveBeenCalledWith(
      DEMO_SESSION_COOKIE,
      "signed-jwt",
      expect.objectContaining({ secure: false }),
    );
  });

  it("verifies the cookie token with FastAPI before returning the principal", async () => {
    cookieStore.get.mockReturnValue({ value: "signed-jwt" });
    vi.mocked(getCurrentDemoPrincipal).mockResolvedValue(approver);

    await expect(requireDemoSession("/approvals?status=pending")).resolves.toEqual({
      accessToken: "signed-jwt",
      principal: approver,
    });
    expect(getCurrentDemoPrincipal).toHaveBeenCalledWith("signed-jwt");
  });

  it("clears an invalid cookie and redirects to login with a safe return path", async () => {
    cookieStore.get.mockReturnValue({ value: "expired-jwt" });
    vi.mocked(getCurrentDemoPrincipal).mockRejectedValue(
      new MeterDeskApiError("Invalid token", 401, "auth.invalid_token"),
    );

    await expect(requireDemoSession("/approvals?status=pending")).rejects.toThrow(
      "REDIRECT:/login?reason=session-expired&returnTo=%2Fapprovals%3Fstatus%3Dpending",
    );
    expect(cookieStore.delete).toHaveBeenCalledWith(DEMO_SESSION_COOKIE);
    expect(redirect).toHaveBeenCalledTimes(1);
  });

  it("redirects an anonymous request without treating it as an expired session", async () => {
    await expect(requireDemoSession("https://evil.example")).rejects.toThrow(
      "REDIRECT:/login?returnTo=%2F",
    );
    expect(cookieStore.delete).not.toHaveBeenCalled();
  });

  it("can explicitly clear the shared browser session", async () => {
    await clearDemoSessionCookie();

    expect(cookieStore.delete).toHaveBeenCalledWith(DEMO_SESSION_COOKIE);
  });
});
