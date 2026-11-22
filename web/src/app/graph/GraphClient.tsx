"use client";
import { useCallback, useState } from "react";
import {
  ReactFlow,
  Handle,
  Position,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection,
  MarkerType,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { MOCK_NCS, MOCK_CLOSURE_REPORT } from "@/lib/mock-data";
import { StatusBadge } from "@/components/StatusBadge";
import { tokens } from "@/lib/tokens";
import type { Link } from "@/lib/types";

// ---- Colour by NC status ---------------------------------------------------
function ncColor(status: string) {
  if (status === "CLOSED") return "#10b981";
  if (status === "REOPENED" || status === "OPEN") return "#ef4444";
  if (status === "PENDING_HEAD_APPROVAL" || status === "TRACE_REVIEW") return tokens.colors.electric;
  return "#f59e0b";
}

// ---- Build graph from golden scenario ------------------------------------
const NC_MAP = Object.fromEntries(MOCK_NCS.map((nc) => [nc.id, nc]));

const INITIAL_NODES: Node[] = [
  {
    id: "NC-0412",
    position: { x: 300, y: 200 },
    data: { nc: NC_MAP["NC-0412"] },
    type: "ncNode",
  },
  {
    id: "NC-0377",
    position: { x: 100, y: 400 },
    data: { nc: NC_MAP["NC-0377"] },
    type: "ncNode",
  },
  {
    id: "NC-0390",
    position: { x: 500, y: 400 },
    data: { nc: NC_MAP["NC-0390"] },
    type: "ncNode",
  },
  {
    id: "NC-0401",
    position: { x: 700, y: 200 },
    data: { nc: NC_MAP["NC-0401"] },
    type: "ncNode",
  },
];

function buildEdges(links: Link[]): Edge[] {
  return links.map((l) => ({
    id: `e-${l.id}`,
    source: l.a,
    target: l.b,
    label: `${(l.score * 100).toFixed(0)}%`,
    labelStyle: { fill: tokens.colors.electric, fontWeight: 700, fontSize: 10 },
    style: { stroke: tokens.colors.electric, strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: tokens.colors.electric },
    animated: true,
    data: { link: l },
  }));
}

const INITIAL_EDGES = buildEdges(MOCK_CLOSURE_REPORT.links);

// ---- Custom node -----------------------------------------------------------
function NcNode({ data }: { data: { nc: (typeof MOCK_NCS)[0] } }) {
  const { nc } = data;
  const color = ncColor(nc.status);
  return (
    <div
      className="relative rounded-xl border bg-slate-900 p-3 shadow-xl"
      style={{ borderColor: color, minWidth: 160 }}
    >
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !border-2 !border-slate-950 !bg-electric" />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="font-mono text-xs font-bold" style={{ color }}>
          {nc.id}
        </span>
        <div className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      </div>
      <p className="text-xs text-slate-300 line-clamp-2 leading-tight">{nc.title}</p>
      <div className="mt-2 flex gap-1 flex-wrap">
        <span
          className="rounded px-1.5 py-0.5 text-[9px] font-semibold"
          style={{ background: `${color}20`, color }}
        >
          {nc.status.replace(/_/g, " ")}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !border-2 !border-slate-950 !bg-electric" />
    </div>
  );
}

const nodeTypes = { ncNode: NcNode };

// ---- Edge detail panel -----------------------------------------------------
function EdgeDetail({ link }: { link: Link | null }) {
  if (!link) return null;
  return (
    <div className="absolute right-4 top-4 w-72 glass rounded-xl p-4 z-10 animate-fade-in">
      <div className="mb-3 flex items-center gap-2">
        <span className="font-mono text-xs font-bold text-electric">{link.a}</span>
        <span className="text-slate-500">→</span>
        <span className="font-mono text-xs font-bold text-electric">{link.b}</span>
        <span className="ml-auto text-xs font-semibold text-slate-200">
          {(link.score * 100).toFixed(0)}% match
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {link.signals.map((s) => (
          <div key={s.name} className="flex flex-col gap-0.5">
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-slate-400">{s.name.replace(/_/g, " ")}</span>
              <span className="font-mono text-electric">+{(s.contribution * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1 rounded-full bg-slate-800">
              <div
                className="h-1 rounded-full bg-electric"
                style={{ width: `${Math.min(s.contribution / link.score, 1) * 100}%` }}
              />
            </div>
            <span className="text-[9px] text-slate-600 italic">{s.evidence}</span>
          </div>
        ))}
      </div>

      {/* Confirm / Reject */}
      <div className="mt-3 flex gap-2">
        <button
          id={`confirm-link-${link.id}`}
          className="flex-1 rounded-lg bg-emerald-500/20 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/30 transition-colors"
        >
          ✓ Confirm Link
        </button>
        <button
          id={`reject-link-${link.id}`}
          className="flex-1 rounded-lg bg-red-500/20 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-500/30 transition-colors"
        >
          ✗ Reject Link
        </button>
      </div>
      <p className="mt-2 text-[9px] text-slate-600">
        Feedback adjusts engine weights via learning loop.
      </p>
    </div>
  );
}

export function GraphClient() {
  const [nodes, , onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);
  const [selectedLink, setSelectedLink] = useState<Link | null>(null);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedLink((edge.data as { link: Link }).link ?? null);
  }, []);

  return (
    <div className="flex flex-col gap-4 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-white">Failure Propagation Graph</h2>
        <p className="text-xs text-slate-500 mt-0.5">Click an edge to inspect signals and confirm/reject</p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-slate-400">
        {[
          { color: tokens.colors.electric, label: "Pending / TRACE Review" },
          { color: "#ef4444", label: "Open / Reopened" },
          { color: "#10b981", label: "Closed" },
          { color: "#f59e0b", label: "In Progress" },
        ].map((l) => (
          <div key={l.label} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: l.color }} />
            {l.label}
          </div>
        ))}
      </div>

      <div className="relative h-[600px] rounded-xl border border-white/5 overflow-hidden">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onEdgeClick={onEdgeClick}
          nodeTypes={nodeTypes}
          fitView
          colorMode="dark"
          className="bg-slate-950"
        >
          <Background color="#1e293b" gap={24} variant={BackgroundVariant.Lines} />
          <Controls />
          <MiniMap
            nodeColor={(n) => ncColor((n.data as { nc: { status: string } }).nc?.status ?? "")}
            className="!bg-slate-900 !border-white/10"
          />
        </ReactFlow>
        <EdgeDetail link={selectedLink} />
      </div>

      {/* Golden scenario summary */}
      <div className="glass rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex h-5 w-5 items-center justify-center rounded bg-electric/20 ring-1 ring-electric/40">
            <span className="text-[9px] font-black text-electric">T</span>
          </div>
          <span className="text-sm font-semibold text-slate-200">Golden Scenario — TRACE Verdict: HOLD</span>
          <StatusBadge value="HOLD" className="ml-auto" />
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          <span className="text-electric font-mono">NC-0412</span> (brake drum bore burr, Line 2) appears
          resolved after a deburring tool replacement. TRACE detects it is linked to unresolved{" "}
          <span className="text-electric font-mono">NC-0377</span> (sharp edge, same tooling root-cause,
          Line 4) and closed-but-recurred{" "}
          <span className="text-electric font-mono">NC-0390</span> (heat treatment, tool change interval
          undefined). Verdict: <span className="text-red-400 font-bold">HOLD</span>.
        </p>
      </div>
    </div>
  );
}
