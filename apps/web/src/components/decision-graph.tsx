"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  DecisionGraph,
  DecisionGraphNode,
  DecisionGraphNodeId,
  DecisionGraphTone,
  WorkbenchScenario,
} from "@/lib/meterdesk-view";

type DecisionOverviewProps = {
  graph: DecisionGraph;
  summary: WorkbenchScenario["decisionSummary"];
};

export function DecisionOverview({ graph, summary }: DecisionOverviewProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<DecisionGraphNodeId>(graph.defaultNodeId);

  useEffect(() => {
    setSelectedNodeId(graph.defaultNodeId);
  }, [graph.defaultNodeId]);

  const selectedNode = useMemo(
    () => graph.nodes.find((node) => node.id === selectedNodeId) ?? graph.nodes[0],
    [graph.nodes, selectedNodeId],
  );

  return (
    <section
      aria-labelledby="decision-overview-heading"
      className="rounded-md border border-meter-line bg-white p-5"
      role="region"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase text-slate-500">Decision overview</p>
          <h2 id="decision-overview-heading" className="mt-2 text-xl font-semibold">
            Decision Overview
          </h2>
          <h3 className="mt-3 text-2xl font-semibold leading-tight">{summary.decisionLabel}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
            {summary.rationale}
          </p>
        </div>
        {summary.runId || summary.policyCitation || summary.complianceStatus ? (
          <div className="flex shrink-0 flex-wrap gap-2 text-xs font-medium lg:max-w-[260px] lg:justify-end">
            {summary.runId ? <SummaryBadge label={`Run ${summary.runId}`} /> : null}
            {summary.policyCitation ? <SummaryBadge label={summary.policyCitation} /> : null}
            {summary.complianceStatus ? (
              <SummaryBadge label={`Compliance ${summary.complianceStatus}`} />
            ) : null}
          </div>
        ) : null}
      </div>

      {graph.summaryBadges.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2 text-xs font-medium">
          {graph.summaryBadges.map((badge) => (
            <SummaryBadge label={badge} key={badge} />
          ))}
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.72fr)]">
        <div className="min-w-0">
          <ol
            aria-label="Decision lineage"
            className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] gap-2"
            data-testid="decision-stepper"
          >
            {graph.nodes.map((node, index) => (
              <li className="min-w-0" key={node.id}>
                <button
                  aria-label={`${node.label} step, ${statusLabel(node)}`}
                  aria-pressed={node.id === selectedNode.id}
                  className={`min-h-[76px] min-w-0 w-full rounded-md border px-3 py-2 text-left transition ${nodeToneClass(
                    node.tone,
                    node.id === selectedNode.id,
                  )}`}
                  onClick={() => setSelectedNodeId(node.id)}
                  type="button"
                >
                  <span className="flex items-center gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-[11px] font-semibold">
                      {index + 1}
                    </span>
                    <span className="whitespace-nowrap text-[11px] font-semibold uppercase leading-tight">
                      {node.label}
                    </span>
                  </span>
                  <span className="mt-2 block whitespace-nowrap text-xs font-semibold leading-tight">
                    {statusLabel(node)}
                  </span>
                </button>
              </li>
            ))}
          </ol>

          {graph.sideOutputs.length > 0 ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {graph.sideOutputs.map((output) => (
                <article
                  className="rounded-md border border-meter-line bg-[#fbfcfe] p-3"
                  key={output.id}
                >
                  <p className="text-xs font-semibold uppercase text-slate-500">
                    Side output - {output.label}
                  </p>
                  <h3 className="mt-2 text-sm font-semibold">{output.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{output.body}</p>
                  {output.refs.length > 0 ? (
                    <p className="mt-2 break-all text-xs font-medium text-meter-blue">
                      Refs: {output.refs.join(", ")}
                    </p>
                  ) : null}
                </article>
              ))}
            </div>
          ) : null}
        </div>

        {selectedNode ? <DecisionGraphInspector node={selectedNode} /> : null}
      </div>
    </section>
  );
}

function SummaryBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-meter-line bg-[#fbfcfe] px-2.5 py-1 text-slate-600">
      {label}
    </span>
  );
}

function DecisionGraphInspector({ node }: { node: DecisionGraphNode }) {
  return (
    <aside className={`rounded-md border p-4 ${inspectorToneClass(node.tone)}`}>
      <p className="text-xs font-semibold uppercase text-slate-500">Inspector</p>
      <h3 className="mt-2 text-lg font-semibold">{node.inspectorTitle}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-700">{node.inspectorBody}</p>

      {node.inspectorDetails.length > 0 ? (
        <dl className="mt-4 space-y-2 text-sm">
          {node.inspectorDetails.map((detail) => (
            <div className="grid gap-1" key={`${detail.label}-${detail.value}`}>
              <dt className="text-xs font-semibold uppercase text-slate-500">{detail.label}</dt>
              <dd className="break-all text-slate-700">{detail.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {node.refs.length > 0 || node.traceIds.length > 0 ? (
        <div className="mt-4 space-y-2 text-xs font-medium">
          {node.refs.length > 0 ? (
            <p className="break-all text-meter-blue">Refs: {node.refs.join(", ")}</p>
          ) : null}
          {node.traceIds.length > 0 ? (
            <p className="break-all text-slate-500">Trace ids: {node.traceIds.join(", ")}</p>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}

function statusLabel(node: DecisionGraphNode) {
  if (node.status === "blocked") {
    return "Blocked";
  }
  if (node.status === "complete") {
    return "Complete";
  }
  if (node.status === "executed") {
    return "Executed";
  }
  if (node.status === "failed") {
    return "Failed";
  }
  if (node.status === "pending") {
    return "Pending";
  }
  if (node.status === "rejected") {
    return "Rejected";
  }
  return "Unavailable";
}

function nodeToneClass(tone: DecisionGraphTone, selected: boolean) {
  const ring = selected ? "ring-2 ring-meter-blue" : "hover:border-meter-blue";
  if (tone === "success") {
    return `${ring} border-meter-mint bg-[#f0fdf8] text-meter-ink`;
  }
  if (tone === "warning") {
    return `${ring} border-meter-amber bg-[#fffaf0] text-meter-ink`;
  }
  if (tone === "danger") {
    return `${ring} border-[#f2b8b8] bg-[#fff5f5] text-meter-ink`;
  }
  if (tone === "info") {
    return `${ring} border-[#c7d7ec] bg-[#f7fbff] text-meter-ink`;
  }
  return `${ring} border-meter-line bg-white text-meter-ink`;
}

function inspectorToneClass(tone: DecisionGraphTone) {
  if (tone === "success") {
    return "border-meter-mint bg-[#f0fdf8]";
  }
  if (tone === "warning") {
    return "border-meter-amber bg-[#fffaf0]";
  }
  if (tone === "danger") {
    return "border-[#f2b8b8] bg-[#fff5f5]";
  }
  if (tone === "info") {
    return "border-[#c7d7ec] bg-[#f7fbff]";
  }
  return "border-meter-line bg-[#fbfcfe]";
}
