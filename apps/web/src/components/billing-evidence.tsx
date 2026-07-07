import type { ReactNode } from "react";

import type { WorkbenchScenario } from "@/lib/meterdesk-view";

type BillingEvidenceProps = {
  evidence: WorkbenchScenario["evidence"];
};

export function BillingEvidence({ evidence }: BillingEvidenceProps) {
  return (
    <section
      aria-labelledby="billing-evidence-heading"
      className="rounded-md border border-meter-line bg-white p-5"
      role="region"
    >
      <h2 id="billing-evidence-heading" className="text-lg font-semibold">
        Billing evidence
      </h2>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <EvidencePanel title="Account">
          <KeyValue label="Customer" value={evidence.account.name} />
          <KeyValue label="Plan" value={evidence.account.plan} />
          <KeyValue label="Owner" value={evidence.account.owner} />
          <KeyValue label="State" value={evidence.account.status} />
        </EvidencePanel>

        <EvidencePanel title="Invoice">
          <KeyValue label="Invoice" value={evidence.invoice.id} />
          <KeyValue label="Period" value={evidence.invoice.period} />
          <KeyValue label="Total" value={evidence.invoice.total} />
          <KeyValue label="Status" value={evidence.invoice.status} />
        </EvidencePanel>
      </div>

      <div className="mt-4 overflow-hidden rounded-md border border-meter-line">
        <div className="grid grid-cols-[1fr_0.6fr_0.7fr] border-b border-meter-line bg-[#f8fafc] px-4 py-3 text-xs font-semibold uppercase text-slate-500">
          <span>Charge</span>
          <span>Amount</span>
          <span>Status</span>
        </div>
        {evidence.charges.map((charge) => (
          <div
            className="grid grid-cols-[1fr_0.6fr_0.7fr] gap-3 border-b border-meter-line px-4 py-3 text-sm last:border-b-0"
            key={charge.id}
          >
            <div className="min-w-0">
              <p className="break-all font-medium">{charge.id}</p>
              <p className="mt-1 text-xs text-slate-500">{charge.capturedAt}</p>
            </div>
            <p className="font-semibold">{charge.amount}</p>
            <div>
              <p>{charge.status}</p>
              <p className="mt-1 text-xs text-slate-500">{charge.processorState}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <EvidencePanel title="Credit ledger">
          <p className="font-semibold">{evidence.credits.label}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{evidence.credits.detail}</p>
        </EvidencePanel>
        <EvidencePanel title="Usage summary">
          <p className="font-semibold">{evidence.usage.label}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{evidence.usage.detail}</p>
        </EvidencePanel>
        <EvidencePanel title="Policy citation">
          <p className="font-semibold">{evidence.policy.id}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{evidence.policy.reason}</p>
        </EvidencePanel>
      </div>
    </section>
  );
}

function EvidencePanel({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-md border border-meter-line bg-[#fbfcfe] p-4">
      <h3 className="text-sm font-semibold uppercase text-slate-500">{title}</h3>
      <div className="mt-3 space-y-3 text-sm">{children}</div>
    </section>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}
