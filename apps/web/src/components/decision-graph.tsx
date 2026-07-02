"use client";

import { useMemo, useState } from "react";

import type {
  DecisionGraph,
  DecisionGraphNode,
  DecisionGraphNodeId,
  DecisionGraphTone,
} from "@/lib/meterdesk-view";

type DecisionGraphCardProps = {
  graph: DecisionGraph;
};

export function DecisionGraphCard({ graph }: DecisionGraphCardProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<DecisionGraphNodeId>(graph.defaultNodeId);
  const selectedNode = useMemo(
    () => graph.nodes.find((node) => node.id === selectedNodeId) ?? graph.nodes[0],
    [graph.nodes, selectedNodeId],
  );

  return (
    <section
      aria-labelledby="decision-graph-heading"
      className="mt-5 rounded-md border border-meter-line bg-white p-4"
      role="region"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Decision Graph</p>
          <h2 id="decision-graph-heading" className="mt-2 text-xl font-semibold">
            Decision Graph
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Why this decision is trustworthy
          </p>
        </div>
        {graph.summaryBadges.length > 0 ? (
          <div className="flex flex-wrap gap-2 text-xs font-medium">
            {graph.summaryBadges.map((badge) => (
              <span
                className="rounded-full border border-meter-line bg-[#fbfcfe] px-2.5 py-1 text-slate-600"
                key={badge}
              >
                {badge}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="mt-4 grid gap-4 2xl:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
        <div>
          <ol className="grid gap-2 md:grid-cols-5">
            {graph.nodes.map((node, index) => (
              <li className="relative" key={node.id}>
                <button
                  aria-pressed={node.id === selectedNode.id}
                  className={`h-full min-h-24 w-full rounded-md border p-3 text-left transition ${nodeToneClass(
                    node.tone,
                    node.id === selectedNode.id,
                  )}`}
                  onClick={() => setSelectedNodeId(node.id)}
                  type="button"
                >
                  <span className="text-xs font-semibold uppercase">{node.label}</span>
                  <span className="mt-2 block text-sm font-semibold">{statusLabel(node)}</span>
                </button>
                {index < graph.nodes.length - 1 ? (
                  <span className="absolute -right-2 top-1/2 hidden -translate-y-1/2 text-slate-400 md:block">
                    -&gt;
                  </span>
                ) : null}
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
