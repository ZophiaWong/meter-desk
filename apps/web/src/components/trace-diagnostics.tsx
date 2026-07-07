"use client";

import { useState } from "react";

import type { WorkbenchScenario } from "@/lib/meterdesk-view";

type TraceDiagnosticsProps = {
  traces: WorkbenchScenario["traces"];
};

export function TraceDiagnostics({ traces }: TraceDiagnosticsProps) {
  const [open, setOpen] = useState(false);

  return (
    <section className="mt-5 rounded-md border border-meter-line bg-[#fbfcfe] p-3">
      <button
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 text-left text-sm font-semibold text-meter-blue"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span>Trace diagnostics</span>
        <span className="text-xs text-slate-500">{traces.length} entries</span>
      </button>

      {open ? (
        <div className="mt-4">
          <h3 className="text-sm font-semibold uppercase text-slate-500">Trace timeline</h3>
          {traces.length === 0 ? (
            <p className="mt-3 rounded-md border border-meter-line bg-white p-3 text-sm text-slate-600">
              No trace entries yet
            </p>
          ) : null}
          <ol className="mt-3 space-y-3">
            {traces.map((trace) => (
              <li className="rounded-md border border-meter-line bg-white p-3" key={trace.id}>
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold">{trace.category}</p>
                  <span className="rounded-full bg-[#fbfcfe] px-2 py-1 text-xs font-medium text-slate-600">
                    {trace.risk} risk
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-700">{trace.label}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{trace.output}</p>
                {trace.governance ? (
                  <p className="mt-2 text-xs font-medium text-slate-500">{trace.governance}</p>
                ) : null}
                <p className="mt-2 text-xs font-medium text-meter-blue">{trace.evidence}</p>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
