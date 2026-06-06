export type ServiceState = "ok" | "down";

export type ServiceStatus = {
  label: string;
  state: ServiceState;
  detail: string;
};

export type SystemStatus = {
  api: ServiceStatus;
  database: ServiceStatus;
  checkedAt: string | null;
};

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 1500;

export async function getSystemStatus(
  apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL,
): Promise<SystemStatus> {
  const normalizedBaseUrl = apiBaseUrl.replace(/\/$/, "");
  const [api, database] = await Promise.all([
    probeEndpoint(`${normalizedBaseUrl}/health`, "API", "FastAPI reachable"),
    probeEndpoint(`${normalizedBaseUrl}/health/db`, "Postgres", "Database reachable"),
  ]);

  return {
    api,
    database,
    checkedAt: new Date().toISOString(),
  };
}

async function probeEndpoint(
  url: string,
  label: string,
  successDetail: string,
): Promise<ServiceStatus> {
  try {
    const response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });

    if (!response.ok) {
      return {
        label,
        state: "down",
        detail: `${label} unavailable`,
      };
    }

    const body = (await response.json()) as { status?: string };
    if (body.status !== "ok") {
      return {
        label,
        state: "down",
        detail: `${label} degraded`,
      };
    }

    return {
      label,
      state: "ok",
      detail: successDetail,
    };
  } catch {
    return {
      label,
      state: "down",
      detail: `${label} unavailable`,
    };
  }
}
