import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { GET } from "./route";

describe("expired demo session route", () => {
  it("clears the path-wide HttpOnly cookie before redirecting to login", () => {
    const request = new NextRequest(
      "http://localhost:3000/auth/session-expired?returnTo=%2Fapprovals",
    );

    const response = GET(request);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/login?reason=session-expired&returnTo=%2Fapprovals",
    );
    expect(response.headers.get("set-cookie")).toEqual(
      expect.stringContaining("meterdesk_demo_session="),
    );
    expect(response.headers.get("set-cookie")).toEqual(expect.stringContaining("Path=/"));
    expect(response.headers.get("set-cookie")).toEqual(expect.stringContaining("Max-Age=0"));
    expect(response.headers.get("set-cookie")).toEqual(expect.stringContaining("HttpOnly"));
    expect(response.headers.get("set-cookie")?.toLowerCase()).toContain("samesite=lax");
  });

  it("sanitizes an external return path and marks HTTPS cleanup cookies Secure", () => {
    const request = new NextRequest(
      "https://meterdesk.example/auth/session-expired?returnTo=https%3A%2F%2Fevil.example",
    );

    const response = GET(request);

    expect(response.headers.get("location")).toBe(
      "https://meterdesk.example/login?reason=session-expired&returnTo=%2F",
    );
    expect(response.headers.get("set-cookie")).toEqual(expect.stringContaining("Secure"));
  });
});
