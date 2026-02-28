import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { WalletProvider } from "@/providers/WalletProvider";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "NILE Security - Solana Smart Contract Intelligence",
  description: "Security scoring for Solana programs and tokens — NILE 4-dimension analysis for the Phantom wallet ecosystem",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <WalletProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 p-8 overflow-auto">{children}</main>
          </div>
        </WalletProvider>
      </body>
    </html>
  );
}
