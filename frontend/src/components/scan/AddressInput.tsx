"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";

interface AddressInputProps {
  onSubmit: (address: string) => void;
  disabled?: boolean;
}

const BASE58_REGEX = /^[1-9A-HJ-NP-Za-km-z]+$/;

function isValidSolanaAddress(address: string): boolean {
  if (address.length < 32 || address.length > 44) return false;
  return BASE58_REGEX.test(address);
}

export function AddressInput({ onSubmit, disabled }: AddressInputProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed) {
      setError("Enter a Solana address");
      return;
    }
    if (trimmed.startsWith("0x")) {
      setError("This looks like an Ethereum address. NILE scans Solana programs.");
      return;
    }
    if (!isValidSolanaAddress(trimmed)) {
      setError("Invalid Solana address (must be 32-44 base58 characters)");
      return;
    }
    setError(null);
    onSubmit(trimmed);
  }, [value, onSubmit]);

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const pasted = e.clipboardData.getData("text").trim();
      if (isValidSolanaAddress(pasted)) {
        e.preventDefault();
        setValue(pasted);
        setError(null);
        onSubmit(pasted);
      }
    },
    [onSubmit],
  );

  return (
    <div className="space-y-2">
      <div className="flex gap-3">
        <input
          type="text"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError(null);
          }}
          onPaste={handlePaste}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder="Paste a Solana program or token address..."
          disabled={disabled}
          className={cn(
            "flex-1 px-4 py-3 bg-gray-900 border rounded-lg text-sm font-mono",
            "placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-nile-500/50",
            "transition-colors",
            error
              ? "border-security-danger/50 focus:ring-security-danger/50"
              : "border-gray-700",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          className={cn(
            "px-6 py-3 rounded-lg text-sm font-medium transition-colors",
            "bg-nile-600 text-white hover:bg-nile-500",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
        >
          {disabled ? "Scanning..." : "Scan"}
        </button>
      </div>
      {error && <p className="text-security-danger text-xs">{error}</p>}
    </div>
  );
}
