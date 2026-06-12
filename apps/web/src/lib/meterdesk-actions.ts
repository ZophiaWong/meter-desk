"use server";

import { revalidatePath } from "next/cache";

import {
  approveRequest,
  rejectRequest,
  runAllEvalCases,
  runEvalCase,
  startAgentRun,
} from "@/lib/meterdesk-api";

const DEFAULT_TICKET_ID = "TCK-1042";

export async function startDefaultAgentRunAction() {
  await startAgentRun(DEFAULT_TICKET_ID);
  revalidatePath("/");
  revalidatePath("/approvals");
}

export async function approveRequestAction(formData: FormData) {
  const approvalId = String(formData.get("approvalId") ?? "");
  if (!approvalId) {
    throw new Error("approvalId is required");
  }
  await approveRequest(approvalId);
  revalidatePath("/");
  revalidatePath("/approvals");
}

export async function rejectRequestAction(formData: FormData) {
  const approvalId = String(formData.get("approvalId") ?? "");
  if (!approvalId) {
    throw new Error("approvalId is required");
  }
  await rejectRequest(approvalId);
  revalidatePath("/");
  revalidatePath("/approvals");
}

export async function runAllEvalCasesAction() {
  await runAllEvalCases();
  revalidatePath("/eval-lab");
}

export async function rerunEvalCaseAction(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  if (!caseId) {
    throw new Error("caseId is required");
  }
  await runEvalCase(caseId);
  revalidatePath("/eval-lab");
}
