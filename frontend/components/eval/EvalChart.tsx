"use client";
import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

interface EvalChartProps {
  baselineResolvedRate: number;
  branchingResolvedRate: number;
  baselineCostPerFix: number | null;
  branchingCostPerFix: number | null;
}

export default function EvalChart({
  baselineResolvedRate,
  branchingResolvedRate,
  baselineCostPerFix,
  branchingCostPerFix,
}: EvalChartProps) {
  const data = [
    {
      metric: "Resolve Rate (%)",
      Baseline: Number((baselineResolvedRate * 100).toFixed(1)),
      Branching: Number((branchingResolvedRate * 100).toFixed(1)),
    },
    {
      metric: "Cost / Fix ($)",
      Baseline: baselineCostPerFix !== null ? Number(baselineCostPerFix.toFixed(4)) : 0,
      Branching: branchingCostPerFix !== null ? Number(branchingCostPerFix.toFixed(4)) : 0,
    },
  ];

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="metric" stroke="var(--text-muted)" fontSize={12} tickLine={false} />
          <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--surface)",
              borderColor: "var(--border)",
              borderRadius: "8px",
              color: "var(--text)",
              fontSize: "12px",
              fontFamily: "var(--font-mono)",
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }}
          />
          <Bar dataKey="Baseline" fill="var(--text-muted)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Branching" fill="var(--accent)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
