"use server";

import { redirect } from "next/navigation";

import { safeReturnTo } from "@/lib/demo-auth";
import { demoLogin } from "@/lib/meterdesk-api";
import { clearDemoSessionCookie, setDemoSessionCookie } from "@/lib/session";

export async function loginAction(formData: FormData): Promise<void> {
  await authenticateSelectedIdentity(formData);
}

export async function switchIdentityAction(formData: FormData): Promise<void> {
  await authenticateSelectedIdentity(formData);
}

export async function logoutAction(): Promise<void> {
  await clearDemoSessionCookie();
  redirect("/login");
}

async function authenticateSelectedIdentity(formData: FormData): Promise<void> {
  const subject = String(formData.get("subject") ?? "");
  if (!subject) {
    throw new Error("subject is required");
  }

  const returnTo = safeReturnTo(String(formData.get("returnTo") ?? "/"));
  const login = await demoLogin(subject);
  await setDemoSessionCookie(login.access_token);
  redirect(returnTo);
}
