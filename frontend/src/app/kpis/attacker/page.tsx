"use client";

import { useEffect, useState } from "react";
import { AttackerMetrics } from "@/components/dashboard/AttackerMetrics";
import { api } from "@/lib/api";
import type { AttackerKPIs } from "@/lib/types";

export default function AttackerKPIsPage() {
  const [data, setData] = useState<AttackerKPIs | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.kpis
      .attacker()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Attacker-Side Intelligence</h1>
        <p className="text-gray-400 mt-1">
          Exploit capabilities, attack vectors, and offensive metrics from EVMbench evaluations
        </p>
      </div>
      {loading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-gray-800 rounded-xl" />
          <div className="h-64 bg-gray-800 rounded-xl" />
        </div>
      ) : (
        <AttackerMetrics data={data ?? undefined} />
      )}
    </div>
  );
}
