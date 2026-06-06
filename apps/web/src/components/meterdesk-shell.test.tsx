import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MeterDeskShell } from "./meterdesk-shell";

const checkedAt = "2026-06-05T12:00:00.000Z";

describe("MeterDeskShell", () => {
  it("renders the minimal product shell with reachable system status", () => {
    render(
      <MeterDeskShell
        status={{
          api: { label: "API", state: "ok", detail: "FastAPI reachable" },
          database: { label: "Postgres", state: "ok", detail: "Database reachable" },
          checkedAt,
        }}
      />,
    );

    expect(screen.getByRole("heading", { name: "MeterDesk" })).toBeInTheDocument();
    expect(screen.getByText("Ticket Workbench")).toBeInTheDocument();
    expect(screen.getByText("Approval Queue")).toBeInTheDocument();
    expect(screen.getByText("Eval Lab")).toBeInTheDocument();
    expect(screen.getByText("FastAPI reachable")).toBeInTheDocument();
    expect(screen.getByText("Database reachable")).toBeInTheDocument();
  });

  it("renders degraded status when backend dependencies are unavailable", () => {
    render(
      <MeterDeskShell
        status={{
          api: { label: "API", state: "down", detail: "FastAPI unavailable" },
          database: { label: "Postgres", state: "down", detail: "Database unavailable" },
          checkedAt: null,
        }}
      />,
    );

    expect(screen.getByText("FastAPI unavailable")).toBeInTheDocument();
    expect(screen.getByText("Database unavailable")).toBeInTheDocument();
  });
});
