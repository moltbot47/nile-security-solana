"use client";

import { useEffect, useState } from "react";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import { api } from "@/lib/api";
import type { Contract } from "@/lib/types";

export default function ContractsPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.contracts
      .list()
      .then(setContracts)
      .catch(() => setContracts([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Smart Contracts</h1>
        <p className="text-gray-400 mt-1">
          Monitored contracts with NILE security scores
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">
          Loading contracts...
        </div>
      ) : contracts.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No contracts monitored yet</p>
          <p className="text-sm">
            Submit a contract address to begin security monitoring
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contracts.map((c) => (
            <div
              key={c.id}
              className="rounded-xl border border-gray-800 p-6 hover:border-nile-500/30 transition-colors cursor-pointer"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold text-lg">{c.name}</h3>
                  <p className="text-sm text-gray-400">{c.chain}</p>
                </div>
                {c.latest_nile_score && (
                  <NileScoreGauge
                    score={c.latest_nile_score.total_score}
                    size="sm"
                  />
                )}
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400 font-mono text-xs truncate max-w-[200px]">
                  {c.address}
                </span>
                {c.is_verified && (
                  <span className="text-nile-400 text-xs">Verified</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
