"use client";

interface LoadingStateProps {
  variant?: "gauge" | "table" | "card" | "inline";
  rows?: number;
}

export function LoadingState({ variant = "card", rows = 5 }: LoadingStateProps) {
  if (variant === "gauge") {
    return (
      <div className="flex flex-col items-center gap-2">
        <div className="w-24 h-24 rounded-full bg-gray-800 animate-pulse" />
        <div className="w-20 h-3 rounded bg-gray-800 animate-pulse" />
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <div className="h-4 w-32 rounded bg-gray-800 animate-pulse" />
            <div className="h-4 w-16 rounded bg-gray-800 animate-pulse" />
            <div className="h-4 w-12 rounded bg-gray-800 animate-pulse" />
            <div className="h-4 w-10 rounded bg-gray-800 animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "inline") {
    return (
      <span className="inline-block w-12 h-4 rounded bg-gray-800 animate-pulse align-middle" />
    );
  }

  // card variant
  return (
    <div className="rounded-xl border border-gray-800 p-6 space-y-3">
      <div className="h-4 w-1/3 rounded bg-gray-800 animate-pulse" />
      <div className="h-8 w-1/2 rounded bg-gray-800 animate-pulse" />
      <div className="h-3 w-2/3 rounded bg-gray-800 animate-pulse" />
    </div>
  );
}
