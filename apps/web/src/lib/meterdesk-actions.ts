"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  approveRequest,
  cancelWorkflow,
  MeterDeskApiError,
  rejectRequest,
  runAllEvalCases,
  runEvalCase,
  startAgentRun,
} from "@/lib/meterdesk-api";
import { clearDemoSessionCookie, requireDemoSession } from "@/lib/session";

const DEFAULT_TICKET_ID = "TCK-1042";

export async function startAgentRunAction(formData: FormData) {
  const ticketId = String(formData.get("ticketId") ?? DEFAULT_TICKET_ID);
  if (!ticketId) {
    throw new Error("ticketId is required");
  }
  const returnTo = ticketReturnTo(ticketId);
  const idempotencyKey = String(formData.get("idempotencyKey") ?? crypto.randomUUID());
  await runAuthenticatedMutation(returnTo, (accessToken) =>
    startAgentRun(ticketId, undefined, accessToken, idempotencyKey),
  );
  revalidatePath("/");
  revalidatePath(`/?ticket=${ticketId}`);
  revalidatePath("/approvals");
}

export async function startDefaultAgentRunAction() {
  const formData = new FormData();
  formData.set("ticketId", DEFAULT_TICKET_ID);
  await startAgentRunAction(formData);
}

export async function cancelWorkflowAction(formData: FormData) {
  const workflowId = String(formData.get("workflowId") ?? "");
  const ticketId = String(formData.get("ticketId") ?? DEFAULT_TICKET_ID);
  const reason = String(formData.get("reason") ?? "Workflow cancelled by support operator.");
  if (!workflowId) {
    throw new Error("workflowId is required");
  }
  const returnTo = ticketReturnTo(ticketId);
  await runAuthenticatedMutation(returnTo, (accessToken) =>
    cancelWorkflow(workflowId, reason, undefined, accessToken),
  );
  revalidatePath("/");
  revalidatePath(returnTo);
  revalidatePath("/approvals");
}

export async function approveRequestAction(formData: FormData) {
  const approvalId = String(formData.get("approvalId") ?? "");
  if (!approvalId) {
    throw new Error("approvalId is required");
  }
  const ticketId = String(formData.get("ticketId") ?? "");
  const returnTo = ticketId ? ticketReturnTo(ticketId) : "/approvals";
  const decisionNote = optionalFormValue(formData, "decisionNote");
  await runAuthenticatedMutation(returnTo, (accessToken) =>
    approveRequest(approvalId, undefined, accessToken, decisionNote),
  );
  revalidatePath("/");
  if (ticketId) {
    revalidatePath(`/?ticket=${ticketId}`);
  }
  revalidatePath("/approvals");
}

export async function rejectRequestAction(formData: FormData) {
  const approvalId = String(formData.get("approvalId") ?? "");
  if (!approvalId) {
    throw new Error("approvalId is required");
  }
  const ticketId = String(formData.get("ticketId") ?? "");
  const returnTo = ticketId ? ticketReturnTo(ticketId) : "/approvals";
  const decisionNote = optionalFormValue(formData, "decisionNote");
  await runAuthenticatedMutation(returnTo, (accessToken) =>
    rejectRequest(approvalId, undefined, accessToken, decisionNote),
  );
  revalidatePath("/");
  if (ticketId) {
    revalidatePath(`/?ticket=${ticketId}`);
  }
  revalidatePath("/approvals");
}

export async function runAllEvalCasesAction() {
  await runAuthenticatedMutation("/eval-lab", (accessToken) =>
    runAllEvalCases(undefined, accessToken),
  );
  revalidatePath("/eval-lab");
}

export async function rerunEvalCaseAction(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  if (!caseId) {
    throw new Error("caseId is required");
  }
  await runAuthenticatedMutation("/eval-lab", (accessToken) =>
    runEvalCase(caseId, undefined, accessToken),
  );
  revalidatePath("/eval-lab");
}

async function runAuthenticatedMutation(
  returnTo: string,
  mutation: (accessToken: string) => Promise<unknown>,
): Promise<void> {
  const session = await requireDemoSession(returnTo);
  try {
    await mutation(session.accessToken);
  } catch (error) {
    if (error instanceof MeterDeskApiError && error.status === 401) {
      await clearDemoSessionCookie();
      const params = new URLSearchParams({
        reason: "session-expired",
        returnTo,
      });
      redirect(`/login?${params.toString()}`);
    }
    if (error instanceof MeterDeskApiError && error.status === 403) {
      const params = new URLSearchParams({ returnTo });
      if (error.requestId) {
        params.set("requestId", error.requestId);
      }
      redirect(`/forbidden?${params.toString()}`);
    }
    throw error;
  }
}

function ticketReturnTo(ticketId: string): string {
  return `/?${new URLSearchParams({ ticket: ticketId }).toString()}`;
}

function optionalFormValue(formData: FormData, name: string): string | undefined {
  const value = String(formData.get(name) ?? "").trim();
  return value || undefined;
}
