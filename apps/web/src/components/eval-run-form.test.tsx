import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EvalRunControlsProvider, EvalRunForm } from "./eval-run-form";

describe("EvalRunForm", () => {
  it("shows loading feedback only on Run all while all eval buttons are locked", async () => {
    const runAll = deferredAction();
    const rerun = deferredAction();

    render(
      <EvalRunControlsProvider>
        <EvalRunForm
          action={runAll.action}
          defaultLabel="Run all evals"
          pendingLabel="Running all evals..."
          runKey="all"
          variant="primary"
        />
        <EvalRunForm
          action={rerun.action}
          ariaLabel="Rerun eval-duplicate-charge-001"
          defaultLabel="Rerun"
          hiddenFields={[{ name: "caseId", value: "eval-duplicate-charge-001" }]}
          pendingLabel="Rerunning..."
          runKey="eval-duplicate-charge-001"
          variant="outline"
        />
      </EvalRunControlsProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Run all evals" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Running all evals..." })).toBeDisabled(),
    );
    expect(screen.getByRole("button", { name: "Rerun eval-duplicate-charge-001" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Rerun eval-duplicate-charge-001" })).toHaveTextContent(
      "Rerun",
    );

    runAll.resolve();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Run all evals" })).toBeEnabled(),
    );
    expect(screen.getByRole("button", { name: "Rerun eval-duplicate-charge-001" })).toBeEnabled();
  });

  it("shows loading feedback only on the clicked Rerun while all eval buttons are locked", async () => {
    const runAll = deferredAction();
    const rerun = deferredAction();

    render(
      <EvalRunControlsProvider>
        <EvalRunForm
          action={runAll.action}
          defaultLabel="Run all evals"
          pendingLabel="Running all evals..."
          runKey="all"
          variant="primary"
        />
        <EvalRunForm
          action={rerun.action}
          ariaLabel="Rerun eval-credit-refund-001"
          defaultLabel="Rerun"
          hiddenFields={[{ name: "caseId", value: "eval-credit-refund-001" }]}
          pendingLabel="Rerunning..."
          runKey="eval-credit-refund-001"
          variant="outline"
        />
      </EvalRunControlsProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Rerun eval-credit-refund-001" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Rerunning..." })).toBeDisabled(),
    );
    expect(screen.getByRole("button", { name: "Run all evals" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Run all evals" })).toHaveTextContent("Run all evals");

    expect(rerun.action).toHaveBeenCalledTimes(1);
    const submittedData = rerun.action.mock.calls[0]?.[0] as FormData;
    expect(submittedData.get("caseId")).toBe("eval-credit-refund-001");
  });
});

function deferredAction() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  const action = vi.fn(async (formData: FormData) => {
    void formData;
    await promise;
  });

  return { action, resolve };
}
