import { AppShell } from "@/components/app-shell";
import { EvalLab } from "@/components/eval-lab";
import { getSystemStatus } from "@/lib/status";
import { requireDemoSession } from "@/lib/session";

export default async function EvalLabPage() {
  const session = await requireDemoSession("/eval-lab");
  const [systemStatus, content] = await Promise.all([
    getSystemStatus(),
    EvalLab({ accessToken: session.accessToken, currentPrincipal: session.principal }),
  ]);
  return (
    <AppShell
      activeSurface="Eval Lab"
      currentPrincipal={session.principal}
      returnTo="/eval-lab"
      status={systemStatus}
    >
      {content}
    </AppShell>
  );
}
