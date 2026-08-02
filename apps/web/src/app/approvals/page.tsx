import { AppShell } from "@/components/app-shell";
import { ApprovalQueue } from "@/components/approval-queue";
import type { ApprovalQueueStatus } from "@/lib/meterdesk-view";
import { getSystemStatus } from "@/lib/status";
import { requireDemoSession } from "@/lib/session";

type ApprovalsPageProps = {
  searchParams?: Promise<{ status?: string }>;
};

const VALID_STATUSES = new Set(["pending", "approved", "rejected", "all"]);

export default async function ApprovalsPage({ searchParams }: ApprovalsPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const status = normalizeStatus(resolvedSearchParams.status);
  const returnTo = status === "pending" ? "/approvals" : `/approvals?status=${status}`;
  const session = await requireDemoSession(returnTo);
  const [systemStatus, content] = await Promise.all([
    getSystemStatus(),
    ApprovalQueue({
      accessToken: session.accessToken,
      currentPrincipal: session.principal,
      status,
    }),
  ]);
  return (
    <AppShell
      activeSurface="Approval Queue"
      currentPrincipal={session.principal}
      returnTo={returnTo}
      status={systemStatus}
    >
      {content}
    </AppShell>
  );
}

function normalizeStatus(value?: string): ApprovalQueueStatus {
  return value && VALID_STATUSES.has(value) ? (value as ApprovalQueueStatus) : "pending";
}
