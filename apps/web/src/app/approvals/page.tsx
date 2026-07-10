import { AppShell } from "@/components/app-shell";
import { ApprovalQueue } from "@/components/approval-queue";
import type { ApprovalQueueStatus } from "@/lib/meterdesk-view";
import { getSystemStatus } from "@/lib/status";

type ApprovalsPageProps = {
  searchParams?: Promise<{ status?: string }>;
};

const VALID_STATUSES = new Set(["pending", "approved", "rejected", "all"]);

export default async function ApprovalsPage({ searchParams }: ApprovalsPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const status = normalizeStatus(resolvedSearchParams.status);
  const [systemStatus, content] = await Promise.all([
    getSystemStatus(),
    ApprovalQueue({ status }),
  ]);
  return (
    <AppShell activeSurface="Approval Queue" status={systemStatus}>
      {content}
    </AppShell>
  );
}

function normalizeStatus(value?: string): ApprovalQueueStatus {
  return value && VALID_STATUSES.has(value) ? (value as ApprovalQueueStatus) : "pending";
}
