import type { WorkbenchScenario } from "@/lib/meterdesk-view";

import { TraceDiagnostics } from "./trace-diagnostics";

type ProofAuditProps = {
  scenario: WorkbenchScenario;
};

export function ProofAudit({ scenario }: ProofAuditProps) {
  return (
    <section
      aria-labelledby="proof-audit-heading"
      className="rounded-md border border-meter-line bg-white p-5"
      role="region"
    >
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Proof & audit</p>
          <h2 id="proof-audit-heading" className="mt-2 text-lg font-semibold">
            Proof & audit
          </h2>
        </div>
        <p className="max-w-xl text-sm leading-6 text-slate-600">
          Trace records, governed action rules, and compliance diagnostics for this ticket.
        </p>
      </div>
      <div className="mt-4 space-y-3">
        <ApprovalDecisionAudit scenario={scenario} />
        <TraceDiagnostics traces={scenario.traces} />
        <GovernanceRulesDrawer scenario={scenario} />
      </div>
    </section>
  );
}

function ApprovalDecisionAudit({ scenario }: ProofAuditProps) {
  const approval = scenario.approval;
  if (!approval?.decisionActorSummary) {
    return null;
  }

  return (
    <details className="rounded-md border border-meter-line bg-[#fbfcfe] p-3">
      <summary className="cursor-pointer list-none text-sm font-semibold text-meter-blue">
        Approval decision audit
      </summary>
      <dl className="mt-4 grid gap-3 text-xs text-slate-600 md:grid-cols-2">
        <AuditField label="Actor" value={approval.decisionActorSummary} />
        <AuditField label="Actor subject" value={approval.decisionActorSubject} />
        <AuditField label="Actor source" value={approval.decisionActorSource} />
        <AuditField label="Request ID" value={approval.decisionRequestId} />
        <AuditField label="Decision note" value={approval.decisionNote} />
      </dl>
    </details>
  );
}

function AuditField({ label, value }: { label: string; value: string | null }) {
  if (!value) {
    return null;
  }
  return (
    <div>
      <dt className="font-semibold text-slate-500">{label}</dt>
      <dd className="mt-1 break-all font-medium text-slate-800">{value}</dd>
    </div>
  );
}

function GovernanceRulesDrawer({ scenario }: ProofAuditProps) {
  const policyCount = scenario.toolPolicies.length;
  const highRiskCount = scenario.toolPolicies.filter((policy) => policy.risk === "High").length;

  return (
    <details className="rounded-md border border-meter-line bg-[#fbfcfe] p-3">
      <summary className="cursor-pointer list-none text-sm font-semibold text-meter-blue">
        {policyCount} governed actions | {highRiskCount} high-risk gate | View rules
      </summary>
      <div className="mt-4 space-y-3">
        <p className="text-xs leading-5 text-slate-500">
          Read-only matrix generated from the backend code-first registry.
        </p>
        {scenario.compliance ? (
          <div className="rounded-md border border-meter-line bg-white p-3 text-xs text-slate-600">
            <h3 className="font-semibold text-slate-800">Compliance diagnostics</h3>
            {scenario.compliance.reasonCodes ? (
              <p className="mt-2">Reason codes: {scenario.compliance.reasonCodes}</p>
            ) : null}
            {scenario.compliance.affectedTraceIds ? (
              <p className="mt-2">Affected traces: {scenario.compliance.affectedTraceIds}</p>
            ) : null}
            {scenario.compliance.missingRefs ? (
              <p className="mt-2">Missing refs: {scenario.compliance.missingRefs}</p>
            ) : null}
            {scenario.compliance.policyVersions ? (
              <p className="mt-2">Policy versions: {scenario.compliance.policyVersions}</p>
            ) : null}
          </div>
        ) : null}
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-2 text-left text-xs">
            <thead className="text-slate-500">
              <tr>
                <th className="pr-3 font-semibold">Action</th>
                <th className="pr-3 font-semibold">Risk</th>
                <th className="pr-3 font-semibold">Gate</th>
                <th className="font-semibold">Refs</th>
              </tr>
            </thead>
            <tbody>
              {scenario.toolPolicies.map((policy) => (
                <tr className="align-top" key={policy.id}>
                  <td className="pr-3">
                    <p className="font-semibold text-slate-800">{policy.id}</p>
                    <p className="mt-1 text-slate-500">{policy.label}</p>
                  </td>
                  <td className="pr-3 font-semibold">{policy.risk}</td>
                  <td className="pr-3 text-slate-600">{policy.gate}</td>
                  <td className="text-slate-600">{policy.requiredRefs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </details>
  );
}
