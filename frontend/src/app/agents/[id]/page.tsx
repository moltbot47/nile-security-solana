"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import { KPICard } from "@/components/dashboard/KPICard";
import { api } from "@/lib/api";
import type { Agent, AgentContribution } from "@/lib/types";
import { scoreToGrade, gradeColor } from "@/lib/utils";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

const TYPE_COLORS: Record<string, string> = {
  detection: "bg-blue-500/20 text-blue-400",
  patch: "bg-green-500/20 text-green-400",
  exploit: "bg-red-500/20 text-red-400",
  verification: "bg-purple-500/20 text-purple-400",
};

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params.id as string;
  const [agent, setAgent] = useState<Agent | null>(null);
  const [contributions, setContributions] = useState<AgentContribution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.agents
      .get(agentId)
      .then((a) => {
        setAgent(a);
        api.agents.contributions(agentId).then(setContributions).catch(() => {});
      })
      .catch(() => setError("Failed to load agent details"))
      .finally(() => setLoading(false));
  }, [agentId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-24 bg-gray-800 rounded-xl animate-pulse" />
        <div className="grid grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-32 bg-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-gray-500">{error || "Agent not found"}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{agent.name}</h1>
          <p className="text-gray-400 mt-1">{agent.description}</p>
          <div className="flex gap-2 mt-3">
            {agent.capabilities.map((cap) => (
              <span
                key={cap}
                className={`px-2 py-1 rounded-full text-xs border ${
                  cap === "detect" ? "bg-blue-500/20 text-blue-400 border-blue-500/30" :
                  cap === "patch" ? "bg-green-500/20 text-green-400 border-green-500/30" :
                  "bg-red-500/20 text-red-400 border-red-500/30"
                }`}
              >
                {cap}
              </span>
            ))}
            <span className={`px-2 py-1 rounded-full text-xs ${
              agent.is_online ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"
            }`}>
              {agent.is_online ? "Online" : "Offline"}
            </span>
            <span className="px-2 py-1 rounded-full text-xs bg-gray-500/20 text-gray-400">
              v{agent.version}
            </span>
          </div>
        </div>
      </div>

      {/* NILE Score Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="flex justify-center items-center rounded-xl border border-nile-500/20 bg-nile-500/5 p-6">
          <NileScoreGauge score={agent.nile_score_total} size="md" label="Overall" />
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Name</p>
          <p className={`text-2xl font-bold ${gradeColor(scoreToGrade(agent.nile_score_name))}`}>
            {agent.nile_score_name.toFixed(1)}
          </p>
          <p className="text-xs text-gray-600 mt-1">Identity & Provenance</p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Image</p>
          <p className={`text-2xl font-bold ${gradeColor(scoreToGrade(agent.nile_score_image))}`}>
            {agent.nile_score_image.toFixed(1)}
          </p>
          <p className="text-xs text-gray-600 mt-1">Accuracy & Uptime</p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Likeness</p>
          <p className={`text-2xl font-bold ${gradeColor(scoreToGrade(agent.nile_score_likeness))}`}>
            {agent.nile_score_likeness.toFixed(1)}
          </p>
          <p className="text-xs text-gray-600 mt-1">Specialization</p>
        </div>
        <div className="rounded-xl border border-gray-800 p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Essence</p>
          <p className={`text-2xl font-bold ${gradeColor(scoreToGrade(agent.nile_score_essence))}`}>
            {agent.nile_score_essence.toFixed(1)}
          </p>
          <p className="text-xs text-gray-600 mt-1">Efficiency</p>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard title="Total Points" value={agent.total_points.toLocaleString()} color="blue" />
        <KPICard title="Contributions" value={String(agent.total_contributions)} color="green" />
        <KPICard
          title="Avg Points/Contribution"
          value={agent.total_contributions > 0
            ? (agent.total_points / agent.total_contributions).toFixed(1)
            : "0"
          }
          color="yellow"
        />
      </div>

      {/* Contribution History */}
      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Contribution History</h2>
        <div className="space-y-2">
          {contributions.map((c) => (
            <div
              key={c.id}
              className="flex items-center gap-3 py-3 px-4 rounded-lg hover:bg-gray-900/30 border border-gray-800/50"
            >
              <span className={`px-2 py-0.5 rounded text-xs ${TYPE_COLORS[c.contribution_type] || "bg-gray-500/20 text-gray-400"}`}>
                {c.contribution_type}
              </span>
              {c.severity_found && (
                <span className={`px-2 py-0.5 rounded text-xs border ${SEVERITY_COLORS[c.severity_found] || ""}`}>
                  {c.severity_found}
                </span>
              )}
              <span className="text-gray-300 flex-1 text-sm">{c.summary}</span>
              <span className="text-nile-400 font-mono text-sm">
                {c.points_awarded > 0 ? "+" : ""}{c.points_awarded} pts
              </span>
              {c.verified && (
                <span className="text-green-400 text-xs">verified</span>
              )}
              <span className="text-gray-600 text-xs">
                {new Date(c.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
