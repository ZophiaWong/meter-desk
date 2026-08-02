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
  handleProtectedApiError,
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

  it("stores the JWT for the API-reported lifetime in an HttpOnly cookie", async () => {
    headerStore.get.mockImplementation((name: string) =>
      name === "x-forwarded-proto" ? "https" : null,
    );

    await setDemoSessionCookie("signed-jwt", 3_600);

    expect(cookieStore.set).toHaveBeenCalledWith(DEMO_SESSION_COOKIE, "signed-jwt", {
      httpOnly: true,
      maxAge: 3_600,
      path: "/",
      sameSite: "lax",
      secure: true,
    });
  });

  it("omits Secure for a local HTTP demo", async () => {
    headerStore.get.mockImplementation((name: string) =>
      name === "origin" ? "http://localhost:3000" : null,
    );

    await setDemoSessionCookie("signed-jwt", 28_800);

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

  it("routes an invalid cookie through a handler that can clear it", async () => {
    cookieStore.get.mockReturnValue({ value: "expired-jwt" });
    vi.mocked(getCurrentDemoPrincipal).mockRejectedValue(
      new MeterDeskApiError("Invalid token", 401, "auth.invalid_token"),
    );

    await expect(requireDemoSession("/approvals?status=pending")).rejects.toThrow(
      "REDIRECT:/auth/session-expired?returnTo=%2Fapprovals%3Fstatus%3Dpending",
    );
    expect(cookieStore.delete).not.toHaveBeenCalled();
    expect(redirect).toHaveBeenCalledTimes(1);
  });

  it("routes a protected business API 401 through the same cookie-clearing handler", () => {
    const error = new MeterDeskApiError("Invalid token", 401, "auth.invalid_token");

    expect(() => handleProtectedApiError(error, "/eval-lab")).toThrow(
      "REDIRECT:/auth/session-expired?returnTo=%2Feval-lab",
    );
  });

  it("does not intercept non-authentication business API failures", () => {
    const error = new MeterDeskApiError("Unavailable", 503, "provider.unavailable");

    expect(handleProtectedApiError(error, "/eval-lab")).toBeUndefined();
    expect(redirect).not.toHaveBeenCalled();
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
