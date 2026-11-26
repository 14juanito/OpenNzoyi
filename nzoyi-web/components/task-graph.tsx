"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Controls, Edge, Node, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import { GraphData } from "@/lib/api";

const TYPE_COLOR: Record<string, string> = {
  goal: "#1F2937",
  intent: "#F59E0B",
  fact: "#6B7280",
  finding: "#EF4444",
  hint: "#EAB308",
};
const REL_COLOR: Record<string, string> = {
  spawns: "#F59E0B",
  yields: "#6B7280",
  proves: "#EF4444",
  derived_from: "#10B981",
};
const LAYER = ["goal", "intent", "fact", "finding", "hint"];

export function TaskGraph({ data }: { data: GraphData }) {
  const { nodes, edges } = useMemo(() => {
    const perLayer: Record<string, number> = {};
    const nodes: Node[] = (data.nodes ?? []).map((n) => {
      const layer = Math.max(0, LAYER.indexOf(n.type));
      const idx = (perLayer[n.type] = (perLayer[n.type] ?? 0) + 1) - 1;
      const label =
        n.content?.title || n.content?.phase || n.content?.kind ||
        n.content?.objective || n.type;
      return {
        id: n.id,
        position: { x: layer * 230, y: idx * 90 },
        data: { label: `${n.type}: ${label}` },
        style: {
          background: "#fff",
          border: `2px solid ${TYPE_COLOR[n.type] ?? "#6B7280"}`,
          borderRadius: 12,
          fontSize: 11,
          padding: 8,
          width: 190,
          color: "#1F2937",
        },
      };
    });
    const edges: Edge[] = (data.edges ?? []).map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: e.relation,
      animated: e.relation === "spawns",
      style: { stroke: REL_COLOR[e.relation] ?? "#9CA3AF" },
      labelStyle: { fontSize: 9, fill: "#6B7280" },
      markerEnd: { type: MarkerType.ArrowClosed, color: REL_COLOR[e.relation] ?? "#9CA3AF" },
    }));
    return { nodes, edges };
  }, [data]);

  if (!nodes.length) {
    return (
      <div className="flex h-[500px] items-center justify-center text-sm text-nzoyi-slate">
        Graphe vide — lancez un audit pour peupler l'exploration.
      </div>
    );
  }

  return (
    <div className="h-[560px] rounded-xl border border-nzoyi-border bg-nzoyi-bg">
      <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
        <Background color="#E5E7EB" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
