import { create } from "zustand";

interface WalletState {
  network: "devnet" | "mainnet-beta";
  setNetwork: (network: "devnet" | "mainnet-beta") => void;
}

export const useWalletStore = create<WalletState>((set) => ({
  network: (process.env.NEXT_PUBLIC_SOLANA_NETWORK as "devnet" | "mainnet-beta") || "devnet",
  setNetwork: (network) => set({ network }),
}));
