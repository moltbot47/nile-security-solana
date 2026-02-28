"use client";

import { useWallet } from "@solana/wallet-adapter-react";
import { useWalletModal } from "@solana/wallet-adapter-react-ui";
import { useCallback } from "react";
import { cn } from "@/lib/utils";

export function ConnectButton() {
  const { publicKey, disconnect, connecting, connected } = useWallet();
  const { setVisible } = useWalletModal();

  const handleClick = useCallback(() => {
    if (connected) {
      disconnect();
    } else {
      setVisible(true);
    }
  }, [connected, disconnect, setVisible]);

  const truncatedAddress = publicKey
    ? `${publicKey.toBase58().slice(0, 4)}...${publicKey.toBase58().slice(-4)}`
    : null;

  return (
    <button
      onClick={handleClick}
      disabled={connecting}
      className={cn(
        "w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors",
        connected
          ? "bg-security-safe/10 text-security-safe border border-security-safe/20 hover:bg-security-safe/20"
          : "bg-nile-600 text-white hover:bg-nile-500",
        connecting && "opacity-50 cursor-wait",
      )}
    >
      {connecting
        ? "Connecting..."
        : connected && truncatedAddress
          ? truncatedAddress
          : "Connect Wallet"}
    </button>
  );
}
