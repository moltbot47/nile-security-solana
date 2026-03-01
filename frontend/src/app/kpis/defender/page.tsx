"use client";

import { useEffect, useState } from "react";
import { DefenderMetrics } from "@/components/dashboard/DefenderMetrics";
import { api } from "@/lib/api";
import type { DefenderKPIs } from "@/lib/types";

export default function DefenderKPIsPage() {
  const [data, setData] = useState<DefenderKPIs | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.kpis
      .defender()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Defender-Side Intelligence</h1>
        <p className="text-gray-400 mt-1">
          Detection recall, patch success, and defensive posture metrics
        </p>
      </div>
      {loading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-gray-800 rounded-xl" />
          <div className="h-64 bg-gray-800 rounded-xl" />
        </div>
      ) : (
        <DefenderMetrics data={data ?? undefined} />
      )}
    </div>
  );
}
