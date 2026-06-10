import { ApprovalQueue } from "@/components/approval-queue";
import type { ApprovalQueueStatus } from "@/lib/meterdesk-view";

type ApprovalsPageProps = {
  searchParams?: Promise<{ status?: string }> | { status?: string };
};

const VALID_STATUSES = new Set(["pending", "approved", "rejected", "all"]);

export default async function ApprovalsPage({ searchParams }: ApprovalsPageProps = {}) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const status = normalizeStatus(resolvedSearchParams.status);
  return ApprovalQueue({ status });
}

function normalizeStatus(value?: string): ApprovalQueueStatus {
  return value && VALID_STATUSES.has(value) ? (value as ApprovalQueueStatus) : "pending";
}
