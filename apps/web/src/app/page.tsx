import { MeterDeskShell } from "@/components/meterdesk-shell";
import { getSystemStatus } from "@/lib/status";

export default async function Home() {
  const status = await getSystemStatus();

  return <MeterDeskShell status={status} />;
}
