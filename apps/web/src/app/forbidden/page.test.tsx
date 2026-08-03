import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/session", () => ({
  requireDemoSession: vi.fn(async () => ({
    accessToken: "approver-token",
    principal: {
      subject: "demo-approver",
      display_name: "Demo Approver",
      role: "approver",
    },
  })),
}));

import ForbiddenPage from "./page";

describe("forbidden page", () => {
  it("explains the role denial without clearing the selected identity", async () => {
    render(
      await ForbiddenPage({
        searchParams: Promise.resolve({
          requestId: "req_denied_123",
          returnTo: "/eval-lab",
        }),
      }),
    );

    expect(screen.getByRole("heading", { name: "Permission denied" })).toBeInTheDocument();
    expect(screen.getByText("Demo Approver")).toBeInTheDocument();
    expect(screen.getByText("req_denied_123")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Return to MeterDesk" })).toHaveAttribute(
      "href",
      "/eval-lab",
    );
    expect(screen.getByRole("link", { name: "Switch identity" })).toHaveAttribute(
      "href",
      "/login?mode=switch&returnTo=%2Feval-lab",
    );
  });
});
