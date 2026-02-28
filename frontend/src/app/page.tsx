"use client";

import { useEffect, useState } from "react";
import { KPICard } from "@/components/dashboard/KPICard";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import { AttackerMetrics } from "@/components/dashboard/AttackerMetrics";
import { DefenderMetrics } from "@/components/dashboard/DefenderMetrics";
import { api } from "@/lib/api";
import type { AttackerKPIs, DefenderKPIs, AssetHealthItem } from "@/lib/types";
import { LoadingState } from "@/components/common/LoadingState";

export default function DashboardPage() {
  const [attackerKPIs, setAttackerKPIs] = useState<AttackerKPIs | null>(null);
  const [defenderKPIs, setDefenderKPIs] = useState<DefenderKPIs | null>(null);
  const [assetHealth, setAssetHealth] = useState<AssetHealthItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [atk, def, health] = await Promise.allSettled([
          api.kpis.attacker(),
          api.kpis.defender(),
          api.kpis.assetHealth(),
        ]);
        if (atk.status === "fulfilled") setAttackerKPIs(atk.value);
        if (def.status === "fulfilled") setDefenderKPIs(def.value);
        if (health.status === "fulfilled") setAssetHealth(health.value.items);
      } catch {
        setError("Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const avgScore = assetHealth.length > 0
    ? assetHealth.reduce((sum, a) => sum + a.nile_score, 0) / assetHealth.length
    : 0;

  const totalVulns = assetHealth.reduce((sum, a) => sum + a.open_vulnerabilities, 0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">NILE Security Dashboard</h1>
        <p className="text-gray-400 mt-1">
          Solana smart contract security intelligence — powered by the NILE scoring engine
        </p>
      </div>

      {/* Overview KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="col-span-1 flex justify-center items-center rounded-xl border border-nile-500/20 bg-nile-500/5 p-6">
          {loading ? (
            <LoadingState variant="gauge" />
          ) : (
            <NileScoreGauge
              score={avgScore}
              size="md"
              label="Avg NILE Score"
            />
          )}
        </div>
        <KPICard
          title="Programs Scanned"
          value={loading ? "..." : String(assetHealth.length)}
          subtitle="Solana programs and tokens"
          color="blue"
        />
        <KPICard
          title="Open Vulnerabilities"
          value={loading ? "..." : String(totalVulns)}
          subtitle="Across all scanned programs"
          color={totalVulns > 10 ? "yellow" : "green"}
        />
        <KPICard
          title="Network"
          value="Solana"
          subtitle="Devnet — mainnet-beta coming soon"
          color="blue"
        />
      </div>

      {error && (
        <div className="rounded-xl border border-security-danger/30 bg-security-danger/5 p-4 text-sm text-security-danger">
          {error} — showing cached/demo data where available.
        </div>
      )}

      {/* Attacker + Defender Metrics */}
      <AttackerMetrics data={attackerKPIs ?? undefined} />
      <DefenderMetrics data={defenderKPIs ?? undefined} />

      {/* Program Security Ratings Table */}
      <div className="rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Program Security Ratings</h2>
        {loading ? (
          <LoadingState variant="table" />
        ) : assetHealth.length === 0 ? (
          <p className="text-gray-500 text-sm py-4 text-center">
            No programs scanned yet. Use the{" "}
            <a href="/scan" className="text-nile-400 hover:underline">Scan page</a>{" "}
            to analyze a Solana program.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-3 px-4">Program</th>
                  <th className="text-left py-3 px-4">Chain</th>
                  <th className="text-center py-3 px-4">NILE Score</th>
                  <th className="text-center py-3 px-4">Grade</th>
                  <th className="text-center py-3 px-4">Open Vulns</th>
                  <th className="text-center py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                {assetHealth.map((c) => (
                  <tr
                    key={c.contract_id}
                    className="border-b border-gray-800/50 hover:bg-gray-900/30"
                  >
                    <td className="py-3 px-4 font-medium font-mono text-xs">
                      {c.contract_name}
                    </td>
                    <td className="py-3 px-4 text-gray-400">Solana</td>
                    <td className="py-3 px-4 text-center">{c.nile_score}</td>
                    <td
                      className={`py-3 px-4 text-center font-bold ${
                        c.nile_score >= 80
                          ? "text-security-safe"
                          : c.nile_score >= 60
                            ? "text-security-warning"
                            : "text-security-danger"
                      }`}
                    >
                      {c.grade}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {c.open_vulnerabilities}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${
                          c.open_vulnerabilities === 0
                            ? "bg-security-safe"
                            : c.open_vulnerabilities <= 3
                              ? "bg-security-warning"
                              : "bg-security-danger"
                        }`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
