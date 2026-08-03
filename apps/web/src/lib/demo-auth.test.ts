import { describe, expect, it } from "vitest";

import {
  canDecideApproval,
  canRunEval,
  canStartAgentRun,
  safeReturnTo,
  type DemoPrincipal,
} from "./demo-auth";

describe("demo auth policy", () => {
  it.each([
    ["support_operator", true, false, false],
    ["approver", false, true, false],
    ["admin", true, true, true],
  ] as const)(
    "maps %s to the expected permissions",
    (role, expectedAgentRun, expectedApproval, expectedEval) => {
      const principal: DemoPrincipal = {
        subject: `demo-${role}`,
        display_name: `Demo ${role}`,
        role,
      };

      expect(canStartAgentRun(principal)).toBe(expectedAgentRun);
      expect(canDecideApproval(principal)).toBe(expectedApproval);
      expect(canRunEval(principal)).toBe(expectedEval);
    },
  );

  it.each([
    ["/", "/"],
    ["/?ticket=TCK-1042", "/?ticket=TCK-1042"],
    ["/approvals?status=approved", "/approvals?status=approved"],
    [undefined, "/"],
    ["", "/"],
    ["https://evil.example", "/"],
    ["//evil.example", "/"],
    ["/\\evil.example", "/"],
    ["/login\nSet-Cookie: bad=1", "/"],
  ])("normalizes returnTo %s to %s", (candidate, expected) => {
    expect(safeReturnTo(candidate)).toBe(expected);
  });
});
