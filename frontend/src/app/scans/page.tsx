"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ScanJob } from "@/lib/types";

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Pending";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ScansPage() {
  const [scans, setScans] = useState<ScanJob[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.scans
      .list(statusFilter || undefined)
      .then(setScans)
      .catch(() => setScans([]))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Security Scans</h1>
        <p className="text-gray-400 mt-1">
          AI-powered audit jobs — detect, patch, and exploit evaluations
        </p>
      </div>

      <div className="flex gap-4">
        <button className="px-4 py-2 bg-nile-600 text-white rounded-lg hover:bg-nile-500 transition-colors text-sm">
          New Scan
        </button>
        <select
          className="px-4 py-2 bg-gray-900 border border-gray-700 text-gray-300 rounded-lg text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800">
              <th className="text-left py-3 px-4">Mode</th>
              <th className="text-left py-3 px-4">Agent</th>
              <th className="text-center py-3 px-4">Status</th>
              <th className="text-right py-3 px-4">Started</th>
            </tr>
          </thead>
          <tbody className="text-gray-300">
            {loading ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-gray-500">
                  Loading scans...
                </td>
              </tr>
            ) : scans.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-gray-500">
                  No scans found
                </td>
              </tr>
            ) : (
              scans.map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-gray-800/50 hover:bg-gray-900/30"
                >
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        s.mode === "detect"
                          ? "bg-nile-500/20 text-nile-400"
                          : s.mode === "patch"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {s.mode}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-400">{s.agent}</td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        s.status === "succeeded"
                          ? "bg-green-500/20 text-green-400"
                          : s.status === "running"
                            ? "bg-yellow-500/20 text-yellow-400"
                            : s.status === "failed"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-gray-500/20 text-gray-400"
                      }`}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-gray-400">
                    {timeAgo(s.started_at ?? s.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
