"use client";
import { useCallback, useEffect } from "react";
import { ReactFlow, useNodesState, useEdgesState, Background, BackgroundVariant, Handle, Position, type Node, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion, useReducedMotion } from "motion/react";
import type { RunState, BranchStatus } from "@/lib/events";

interface BranchNodeData extends Record<string, unknown> {
  label: string;
  strategy: string;
  status: BranchStatus;
  isWinner: boolean;
  score: number | null;
  diff_lines: number | null;
}

type BranchNode = Node<BranchNodeData, "branch">;

function statusColor(status: BranchStatus, isWinner: boolean): { border: string; bg: string; text: string } {
  if (isWinner) return { border: "var(--accent)", bg: "var(--accent)", text: "var(--accent-foreground)" };
  if (status === "passed") return { border: "var(--pass)", bg: "var(--surface)", text: "var(--pass)" };
  if (status === "failed") return { border: "var(--fail)", bg: "var(--surface)", text: "var(--fail)" };
  if (status === "cancelled") return { border: "var(--border)", bg: "var(--surface)", text: "var(--text-muted)" };
  return { border: "var(--accent)", bg: "var(--surface)", text: "var(--text)" };
}

function BranchNodeComponent({ data }: { data: BranchNodeData }) {
  const prefersReduced = useReducedMotion();
  const colors = statusColor(data.status, data.isWinner);
  const isPulsing = data.status === "running" && !prefersReduced;

  return (
    <motion.div
      layout={!prefersReduced}
      initial={prefersReduced ? false : { opacity: 0, scale: 0.8 }}
      animate={{
        opacity: data.status === "cancelled" ? 0.4 : 1,
        scale: 1,
        boxShadow: data.isWinner && !prefersReduced ? ["0 0 0 0px var(--accent)", "0 0 16px 4px var(--accent)", "0 0 0 0px var(--accent)"] : undefined,
      }}
      transition={{
        opacity: { duration: 0.3 },
        scale: { type: "spring", stiffness: 300, damping: 20, delay: 0.1 },
        boxShadow: data.isWinner ? { duration: 0.8, repeat: 0 } : undefined,
      }}
      className="rounded-xl px-4 py-3 min-w-[160px] text-center relative"
      style={{ background: colors.bg, border: `2px solid ${colors.border}` }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "var(--border)" }} />
      {isPulsing && (
        <span
          className="absolute inset-0 rounded-xl animate-ping pointer-events-none"
          style={{ border: `1px solid var(--accent)`, opacity: 0.3 }}
        />
      )}
      <div className="text-sm font-semibold font-mono" style={{ color: colors.text }}>
        {data.label}
        {data.status === "cancelled" && " ⏹"}
        {data.status === "passed" && !data.isWinner && " ✓"}
        {data.status === "failed" && " ✗"}
        {data.isWinner && " ★"}
      </div>
      <div className="text-xs mt-1 truncate max-w-[160px]" style={{ color: "var(--text-muted)" }}>{data.strategy}</div>
      {data.score !== null && (
        <div className="text-xs mt-1 font-mono" style={{ color: "var(--text-muted)" }}>
          score: {data.score.toFixed(2)}
          {data.diff_lines !== null ? ` · ${data.diff_lines}L` : ""}
        </div>
      )}
      <Handle type="source" position={Position.Right} style={{ background: "var(--border)" }} />
    </motion.div>
  );
}

const nodeTypes = { branch: BranchNodeComponent };

const ROOT_NODE_ID = "__root__";

export default function BranchBoard({ state }: { state: RunState }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<BranchNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const buildGraph = useCallback(() => {
    const branchIds = Object.keys(state.branches);
    if (branchIds.length === 0) return;

    const rootNode: BranchNode = {
      id: ROOT_NODE_ID,
      type: "branch",
      position: { x: 0, y: (branchIds.length - 1) * 45 },
      data: {
        label: "Base",
        strategy: "checkpoint",
        status: "passed",
        isWinner: false,
        score: null,
        diff_lines: null,
      },
    };

    const branchNodes: BranchNode[] = branchIds.map((id, i) => {
      const b = state.branches[id];
      return {
        id,
        type: "branch",
        position: { x: 280, y: i * 90 },
        data: {
          label: id,
          strategy: b.strategy,
          status: b.status,
          isWinner: state.winner === id,
          score: b.score,
          diff_lines: b.diff_lines,
        },
      };
    });

    const newEdges: Edge[] = branchIds.map((id) => ({
      id: `${ROOT_NODE_ID}->${id}`,
      source: ROOT_NODE_ID,
      target: id,
      animated: state.branches[id].status === "running",
      style: { stroke: "var(--border)" },
    }));

    setNodes([rootNode, ...branchNodes]);
    setEdges(newEdges);
  }, [state.branches, state.winner, setNodes, setEdges]);

  useEffect(() => { buildGraph(); }, [buildGraph]);

  if (Object.keys(state.branches).length === 0) {
    return (
      <div
        className="flex items-center justify-center h-full rounded-lg text-sm"
        style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
      >
        Branches will appear here after forking
      </div>
    );
  }

  return (
    <div
      className="rounded-lg overflow-hidden h-full"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        colorMode="dark"
        proOptions={{ hideAttribution: true }}
        style={{ background: "var(--surface)" }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--border)" />
      </ReactFlow>
    </div>
  );
}
