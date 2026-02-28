"use client";

import { AddressInput } from "@/components/scan/AddressInput";
import { ScoreResult } from "@/components/scan/ScoreResult";
import { VulnerabilityTable } from "@/components/scan/VulnerabilityTable";
import { useScan } from "@/store/scan";

export default function ScanPage() {
  const { scanning, result, error, submitScan, history } = useScan();

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Hero */}
      <div className="text-center space-y-3 pt-8">
        <h1 className="text-4xl font-bold">
          <span className="text-nile-400">NILE</span> Security Scanner
        </h1>
        <p className="text-gray-400 max-w-xl mx-auto">
          Paste any Solana program or token address to get an instant security
          score across 4 dimensions: Name, Image, Likeness, and Essence.
        </p>
      </div>

      {/* Address Input */}
      <AddressInput onSubmit={submitScan} disabled={scanning} />

      {/* Scanning indicator */}
      {scanning && (
        <div className="text-center py-12">
          <div className="inline-flex items-center gap-3 text-nile-400">
            <div className="w-5 h-5 border-2 border-nile-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">
              Analyzing on-chain data and matching exploit patterns...
            </span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-security-danger/30 bg-security-danger/5 p-4">
          <p className="text-security-danger text-sm">{error}</p>
        </div>
      )}

      {/* Result */}
      {result && !scanning && (
        <div className="space-y-6">
          <ScoreResult result={result} />
          <VulnerabilityTable matches={result.exploit_matches} />
        </div>
      )}

      {/* Recent scans */}
      {history.length > 0 && !scanning && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400">Recent Scans</h3>
          <div className="space-y-2">
            {history.slice(0, 5).map((scan, i) => (
              <button
                key={`${scan.address}-${i}`}
                onClick={() => submitScan(scan.address)}
                className="w-full flex items-center justify-between px-4 py-2 rounded-lg
                  border border-gray-800 hover:border-gray-700 transition-colors text-sm"
              >
                <span className="font-mono text-gray-400 truncate max-w-[300px]">
                  {scan.address}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">{scan.analysis_type}</span>
                  <span className="font-medium">
                    {scan.grade} ({scan.total_score.toFixed(0)})
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
