import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ApprovalsPage from "./approvals/page";
import EvalLabPage from "./eval-lab/page";

describe("M1 thin routes", () => {
  it("renders the pending refund in the Approval Queue route", async () => {
    render(await ApprovalsPage());

    expect(screen.getByRole("heading", { name: "Approval Queue" })).toBeInTheDocument();
    expect(screen.getByText("Original refund pending approval")).toBeInTheDocument();
    expect(screen.getByText("TCK-1042")).toBeInTheDocument();
    expect(screen.getByText("$1,248.00")).toBeInTheDocument();
    expect(screen.getByText("Mutation blocked until human approval")).toBeInTheDocument();
  });

  it("renders the static Duplicate Charge eval overview in the Eval Lab route", async () => {
    render(await EvalLabPage());

    expect(screen.getByRole("heading", { name: "Eval Lab" })).toBeInTheDocument();
    expect(screen.getByText("Duplicate Charge golden path")).toBeInTheDocument();
    expect(screen.getByText("Outcome correctness")).toBeInTheDocument();
    expect(screen.getByText("Approval routing")).toBeInTheDocument();
    expect(screen.getByText("Required evidence")).toBeInTheDocument();
    expect(screen.getByText("Trace checks inspect evidence and approval gating.")).toBeInTheDocument();
  });
});
