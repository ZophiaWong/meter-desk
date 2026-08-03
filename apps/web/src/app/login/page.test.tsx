import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import LoginPage from "./page";

const identities = [
  {
    subject: "demo-support-operator",
    display_name: "Demo Support Operator",
    role: "support_operator",
  },
  {
    subject: "demo-approver",
    display_name: "Demo Approver",
    role: "approver",
  },
  {
    subject: "demo-admin",
    display_name: "Demo Admin",
    role: "admin",
  },
];

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("demo login page", () => {
  it("renders the three fixed identities and sanitizes returnTo", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(identities), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        }),
      ),
    );

    render(
      await LoginPage({
        searchParams: Promise.resolve({
          reason: "session-expired",
          returnTo: "https://evil.example/phish",
        }),
      }),
    );

    expect(screen.getByRole("heading", { name: "Choose a demo identity" })).toBeInTheDocument();
    expect(
      screen.getByText("Your demo session expired. Choose an identity to continue."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Continue as Demo Support Operator" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Continue as Demo Approver" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue as Demo Admin" })).toBeInTheDocument();
    expect(document.querySelectorAll('input[name="returnTo"][value="/"]')).toHaveLength(3);
    expect(screen.getByText("Local demo authentication only")).toBeInTheDocument();
  });

  it("labels the same identity picker as a switch flow", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(identities), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        }),
      ),
    );

    render(
      await LoginPage({
        searchParams: Promise.resolve({ mode: "switch", returnTo: "/approvals" }),
      }),
    );

    expect(screen.getByRole("heading", { name: "Switch demo identity" })).toBeInTheDocument();
    expect(document.querySelectorAll('input[name="returnTo"][value="/approvals"]')).toHaveLength(
      3,
    );
  });
});
