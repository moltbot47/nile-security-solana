"use client";

import type { SolanaScanResult } from "@/lib/types";
import { NileScoreGauge } from "@/components/dashboard/NileScoreGauge";
import { cn, gradeColor } from "@/lib/utils";

interface ScoreResultProps {
  result: SolanaScanResult;
}

function DimensionBar({
  label,
  score,
  max = 100,
}: {
  label: string;
  score: number;
  max?: number;
}) {
  const pct = Math.min(100, (score / max) * 100);
  const color =
    score >= 80
      ? "bg-security-safe"
      : score >= 60
        ? "bg-yellow-500"
        : score >= 40
          ? "bg-orange-500"
          : "bg-security-danger";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">{label}</span>
        <span className="font-medium">{score.toFixed(1)}</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-1000", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function ScoreResult({ result }: ScoreResultProps) {
  return (
    <div className="rounded-xl border border-gray-800 bg-[#111] p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold">Scan Result</h2>
            <span
              className={cn(
                "px-2 py-0.5 rounded text-xs font-medium",
                result.analysis_type === "program"
                  ? "bg-nile-500/20 text-nile-400"
                  : "bg-purple-500/20 text-purple-400",
              )}
            >
              {result.analysis_type}
            </span>
          </div>
          <p className="text-gray-500 text-sm font-mono mt-1">{result.address}</p>
        </div>
        <NileScoreGauge score={result.total_score} size="md" />
      </div>

      {/* Grade banner */}
      <div
        className={cn(
          "text-center py-3 rounded-lg border",
          result.total_score >= 80
            ? "bg-security-safe/5 border-security-safe/20"
            : result.total_score >= 60
              ? "bg-yellow-500/5 border-yellow-500/20"
              : "bg-security-danger/5 border-security-danger/20",
        )}
      >
        <span className="text-gray-400 text-sm">NILE Grade: </span>
        <span className={cn("text-lg font-bold", gradeColor(result.grade))}>
          {result.grade}
        </span>
        <span className="text-gray-500 text-sm ml-2">
          ({result.total_score.toFixed(1)}/100)
        </span>
      </div>

      {/* 4 Dimension Bars */}
      <div className="grid grid-cols-1 gap-4">
        <DimensionBar label="Name (Identity & Reputation)" score={result.scores.name} />
        <DimensionBar label="Image (Security Posture)" score={result.scores.image} />
        <DimensionBar
          label="Likeness (Pattern Matching)"
          score={result.scores.likeness}
        />
        <DimensionBar label="Essence (Code Quality)" score={result.scores.essence} />
      </div>

      {/* Exploit matches count */}
      {result.exploit_matches.length > 0 && (
        <div className="flex items-center gap-2 text-security-danger text-sm">
          <span className="font-medium">
            {result.exploit_matches.length} exploit pattern
            {result.exploit_matches.length !== 1 ? "s" : ""} matched
          </span>
        </div>
      )}
    </div>
  );
}
