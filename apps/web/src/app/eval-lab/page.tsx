import { AppShell } from "@/components/app-shell";
import { EvalLab } from "@/components/eval-lab";
import { getSystemStatus } from "@/lib/status";

export default async function EvalLabPage() {
  const [systemStatus, content] = await Promise.all([getSystemStatus(), EvalLab()]);
  return (
    <AppShell activeSurface="Eval Lab" status={systemStatus}>
      {content}
    </AppShell>
  );
}
