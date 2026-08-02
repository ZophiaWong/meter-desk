import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

import { safeReturnTo, type DemoPrincipal } from "@/lib/demo-auth";
import { getCurrentDemoPrincipal, MeterDeskApiError } from "@/lib/meterdesk-api";

export const DEMO_SESSION_COOKIE = "meterdesk_demo_session";
export const DEMO_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60;

export type DemoSession = {
  accessToken: string;
  principal: DemoPrincipal;
};

export async function setDemoSessionCookie(accessToken: string): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(DEMO_SESSION_COOKIE, accessToken, {
    httpOnly: true,
    maxAge: DEMO_SESSION_MAX_AGE_SECONDS,
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
      await clearDemoSessionCookie();
      redirect(loginPath(destination, "session-expired"));
    }
    throw error;
  }
}

function loginPath(returnTo: string, reason?: "session-expired"): string {
  const params = new URLSearchParams();
  if (reason) {
    params.set("reason", reason);
  }
  params.set("returnTo", returnTo);
  return `/login?${params.toString()}`;
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
