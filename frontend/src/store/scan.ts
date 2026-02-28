import { create } from "zustand";
import type { SolanaScanResult } from "@/lib/types";
import { api } from "@/lib/api";

interface ScanState {
  address: string;
  scanning: boolean;
  result: SolanaScanResult | null;
  error: string | null;
  history: SolanaScanResult[];

  setAddress: (address: string) => void;
  submitScan: (address: string) => Promise<void>;
  clearResult: () => void;
}

export const useScan = create<ScanState>((set, get) => ({
  address: "",
  scanning: false,
  result: null,
  error: null,
  history: [],

  setAddress: (address) => set({ address }),

  submitScan: async (address) => {
    set({ scanning: true, error: null, result: null });
    try {
      const result = await api.scan.solana(address);
      set((state) => ({
        scanning: false,
        result,
        history: [result, ...state.history].slice(0, 20),
      }));
    } catch (e) {
      set({
        scanning: false,
        error: e instanceof Error ? e.message : "Scan failed",
      });
    }
  },

  clearResult: () => set({ result: null, error: null }),
}));
