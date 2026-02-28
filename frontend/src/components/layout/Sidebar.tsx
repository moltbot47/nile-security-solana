"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ConnectButton } from "@/components/wallet/ConnectButton";
import { useWalletStore } from "@/store/wallet";

const navItems = [
  { href: "/", label: "Dashboard", icon: "grid" },
  { href: "/scan", label: "Scan Program", icon: "search", highlight: true },
  { href: "/contracts", label: "Contracts", icon: "file" },
  { href: "/scans", label: "Scan History", icon: "list" },
  { href: "/kpis/attacker", label: "Attacker KPIs", icon: "zap" },
  { href: "/kpis/defender", label: "Defender KPIs", icon: "shield" },
  { href: "/benchmarks", label: "Benchmarks", icon: "bar-chart" },
  { href: "/agents", label: "Agents", icon: "users" },
  { href: "/ecosystem", label: "Ecosystem", icon: "globe" },
  { href: "/persons", label: "Persons", icon: "user" },
  { href: "/market", label: "Market", icon: "trending-up" },
  { href: "/portfolio", label: "Portfolio", icon: "wallet" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { network } = useWalletStore();

  return (
    <aside className="w-64 border-r border-gray-800 bg-[#0d0d0d] min-h-screen p-4 flex flex-col">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">
          <span className="text-nile-400">NILE</span>
          <span className="text-gray-500 text-sm ml-2">Security</span>
        </h1>
        <div className="flex items-center gap-2 mt-1">
          <p className="text-xs text-gray-600">Solana Program Intelligence</p>
          <span className={cn(
            "text-[10px] px-1.5 py-0.5 rounded font-medium",
            network === "mainnet-beta"
              ? "bg-security-safe/20 text-security-safe"
              : "bg-purple-500/20 text-purple-400",
          )}>
            {network === "mainnet-beta" ? "mainnet" : network}
          </span>
        </div>
      </div>

      {/* Wallet */}
      <div className="mb-4">
        <ConnectButton />
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block px-3 py-2 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-nile-500/10 text-nile-400 border border-nile-500/20"
                  : item.highlight
                    ? "text-nile-300 hover:text-nile-200 hover:bg-nile-500/10 font-medium"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-4 border-t border-gray-800">
        <div className="text-xs text-gray-600">
          <p>NILE v0.3.0 — Solana</p>
          <p>Phantom Ecosystem</p>
        </div>
      </div>
    </aside>
  );
}
