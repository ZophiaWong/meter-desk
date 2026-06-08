import { MeterDeskShell } from "@/components/meterdesk-shell";
import { getDefaultWorkbenchScenario } from "@/lib/meterdesk-view";
import { getSystemStatus } from "@/lib/status";

export default async function Home() {
  const [status, scenarioResult] = await Promise.all([
    getSystemStatus(),
    getDefaultWorkbenchScenario()
      .then((scenario) => ({ scenario }))
      .catch((error: unknown) => ({
        dataError: error instanceof Error ? error.message : "FastAPI domain data unavailable",
      })),
  ]);

  return <MeterDeskShell status={status} {...scenarioResult} />;
}
