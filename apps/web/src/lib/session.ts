import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

import { safeReturnTo, type DemoPrincipal } from "@/lib/demo-auth";
import { getCurrentDemoPrincipal, MeterDeskApiError } from "@/lib/meterdesk-api";

export const DEMO_SESSION_COOKIE = "meterdesk_demo_session";

export type DemoSession = {
  accessToken: string;
  principal: DemoPrincipal;
};

export async function setDemoSessionCookie(
  accessToken: string,
  expiresInSeconds: number,
): Promise<void> {
  if (!Number.isSafeInteger(expiresInSeconds) || expiresInSeconds <= 0) {
    throw new Error("Invalid demo session expiry.");
  }

  const cookieStore = await cookies();
  cookieStore.set(DEMO_SESSION_COOKIE, accessToken, {
    httpOnly: true,
    maxAge: expiresInSeconds,
    path: "/",
    sameSite: "lax",
    secure: await requestUsesHttps(),
  });
}

export async function clearDemoSessionCookie(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(DEMO_SESSION_COOKIE);
}

export async function requireDemoSession(returnTo = "/"): Promise<DemoSession> {
  const destination = safeReturnTo(returnTo);
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(DEMO_SESSION_COOKIE)?.value;

  if (!accessToken) {
    redirect(loginPath(destination));
  }

  try {
    const principal = await getCurrentDemoPrincipal(accessToken);
    return { accessToken, principal };
  } catch (error) {
    if (error instanceof MeterDeskApiError && error.status === 401) {
      redirect(sessionExpiredPath(destination));
    }
    throw error;
  }
}

export function handleProtectedApiError(error: unknown, returnTo = "/"): void {
  if (error instanceof MeterDeskApiError && error.status === 401) {
    redirect(sessionExpiredPath(safeReturnTo(returnTo)));
  }
}

function loginPath(returnTo: string): string {
  const params = new URLSearchParams();
  params.set("returnTo", returnTo);
  return `/login?${params.toString()}`;
}

function sessionExpiredPath(returnTo: string): string {
  const params = new URLSearchParams({ returnTo });
  return `/auth/session-expired?${params.toString()}`;
}

async function requestUsesHttps(): Promise<boolean> {
  const requestHeaders = await headers();
  const forwardedProtocol = requestHeaders.get("x-forwarded-proto")?.split(",")[0]?.trim();
  if (forwardedProtocol) {
    return forwardedProtocol.toLowerCase() === "https";
  }

  const origin = requestHeaders.get("origin");
  return origin ? origin.toLowerCase().startsWith("https://") : false;
}
