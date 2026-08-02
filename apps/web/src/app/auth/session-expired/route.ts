import { NextRequest, NextResponse } from "next/server";

import { safeReturnTo } from "@/lib/demo-auth";
import { DEMO_SESSION_COOKIE } from "@/lib/session";

export function GET(request: NextRequest): NextResponse {
  const returnTo = safeReturnTo(request.nextUrl.searchParams.get("returnTo") ?? undefined);
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("reason", "session-expired");
  loginUrl.searchParams.set("returnTo", returnTo);

  const response = NextResponse.redirect(loginUrl);
  response.cookies.set(DEMO_SESSION_COOKIE, "", {
    expires: new Date(0),
    httpOnly: true,
    maxAge: 0,
    path: "/",
    sameSite: "lax",
    secure: requestUsesHttps(request),
  });
  return response;
}

function requestUsesHttps(request: NextRequest): boolean {
  const forwardedProtocol = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  if (forwardedProtocol) {
    return forwardedProtocol.toLowerCase() === "https";
  }
  return request.nextUrl.protocol === "https:";
}
