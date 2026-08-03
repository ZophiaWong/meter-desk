import { MeterDeskShell } from "@/components/meterdesk-shell";
import { getWorkbenchScenario } from "@/lib/meterdesk-view";
import { getSystemStatus } from "@/lib/status";
import { handleProtectedApiError, requireDemoSession } from "@/lib/session";

type HomeProps = {
  searchParams?: Promise<{ ticket?: string }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const ticketId =
      typeof resolvedSearchParams.ticket === "string" ? resolvedSearchParams.ticket : undefined;
  const returnTo = ticketId ? `/?ticket=${encodeURIComponent(ticketId)}` : "/";
  const session = await requireDemoSession(returnTo);

  const [status, scenarioResult] = await Promise.all([
    getSystemStatus(),
    getWorkbenchScenario(ticketId, session.accessToken)
      .then((scenario) => ({ scenario }))
      .catch((error: unknown) => {
        handleProtectedApiError(error, returnTo);
        return {
          dataError: error instanceof Error ? error.message : "FastAPI domain data unavailable",
        };
      }),
  ]);

  return (
    <MeterDeskShell
      currentPrincipal={session.principal}
      status={status}
      {...scenarioResult}
    />
  );
}
