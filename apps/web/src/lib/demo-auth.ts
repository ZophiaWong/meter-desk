export type DemoRole = "support_operator" | "approver" | "admin";

export type DemoPrincipal = {
  subject: string;
  display_name: string;
  role: DemoRole;
};

export const AGENT_RUN_PERMISSION_EXPLANATION =
  "Requires the support operator or admin role";
export const APPROVAL_PERMISSION_EXPLANATION = "Requires the approver or admin role";
export const EVAL_PERMISSION_EXPLANATION = "Requires the admin role";

export function canStartAgentRun(principal: DemoPrincipal): boolean {
  return principal.role === "support_operator" || principal.role === "admin";
}

export function canDecideApproval(principal: DemoPrincipal): boolean {
  return principal.role === "approver" || principal.role === "admin";
}

export function canRunEval(principal: DemoPrincipal): boolean {
  return principal.role === "admin";
}

export function formatDemoRole(role: DemoRole): string {
  return role
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function safeReturnTo(candidate?: string): string {
  if (
    !candidate ||
    !candidate.startsWith("/") ||
    candidate.startsWith("//") ||
    candidate.includes("\\") ||
    /[\u0000-\u001f\u007f]/.test(candidate)
  ) {
    return "/";
  }

  return candidate;
}
