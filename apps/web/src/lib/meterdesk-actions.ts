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

export async function startAgentRunAction(formData: FormData) {
  const ticketId = String(formData.get("ticketId") ?? DEFAULT_TICKET_ID);
  if (!ticketId) {
    throw new Error("ticketId is required");
  }
  await startAgentRun(ticketId);
  revalidatePath("/");
  revalidatePath(`/?ticket=${ticketId}`);
  revalidatePath("/approvals");
}

export async function startDefaultAgentRunAction() {
  const formData = new FormData();
  formData.set("ticketId", DEFAULT_TICKET_ID);
  await startAgentRunAction(formData);
}

export async function approveRequestAction(formData: FormData) {
  const approvalId = String(formData.get("approvalId") ?? "");
  if (!approvalId) {
    throw new Error("approvalId is required");
  }
  const ticketId = String(formData.get("ticketId") ?? "");
  await approveRequest(approvalId);
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
  await rejectRequest(approvalId);
  revalidatePath("/");
  if (ticketId) {
    revalidatePath(`/?ticket=${ticketId}`);
  }
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
