"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Item = { href: string; label: string; icon: string };

const functions: Item[] = [
  { href: "/", label: "Dashboard", icon: "grid" },
  { href: "/chat", label: "Chat", icon: "chat" },
  { href: "/tasks", label: "Tâches", icon: "list" },
  { href: "/findings", label: "Findings", icon: "bug" },
  { href: "/attack", label: "ATT&CK", icon: "target" },
  { href: "/telemetry", label: "Télémétrie", icon: "pulse" },
  { href: "/traffic", label: "Trafic", icon: "activity" },
  { href: "/assets", label: "Actifs", icon: "share" },
];

const system: Item[] = [
  { href: "/approvals", label: "Approbations", icon: "shield" },
  { href: "/settings", label: "Paramètres", icon: "settings" },
];

const paths: Record<string, string> = {
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
  chat: "M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  bug: "M8 2l1.5 1.5M16 2l-1.5 1.5M12 20v-9M5 13H2m20 0h-3M6 9a6 6 0 0112 0v4a6 6 0 01-12 0zM5 7L3 5m16 2l2-2M5 19l-2 2m16-2l2 2",
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  target: "M12 12m-9 0a9 9 0 1018 0 9 9 0 10-18 0M12 12m-5 0a5 5 0 1010 0 5 5 0 10-10 0M12 12m-1 0a1 1 0 102 0 1 1 0 10-2 0",
  pulse: "M3 12h4l2-7 4 14 2-7h6",
  share: "M18 8a3 3 0 10-2.83-4M6 15a3 3 0 100 6 3 3 0 000-6zm12 0a3 3 0 100 6 3 3 0 000-6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  settings: "M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.6a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9c.14.63.67 1.09 1.31 1.09H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z",
};

function Row({ it, active }: { it: Item; active: boolean }) {
  return (
    <Link
      href={it.href}
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
        active
          ? "bg-nzoyi-orange/10 text-nzoyi-orange"
          : "text-nzoyi-slate hover:bg-nzoyi-bg hover:text-nzoyi-ink"
      }`}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
           strokeLinecap="round" strokeLinejoin="round" className="h-[18px] w-[18px] shrink-0">
        <path d={paths[it.icon]} />
      </svg>
      {it.label}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-nzoyi-border bg-white md:flex">
      <Link href="/" className="flex items-center gap-2 px-5 py-4">
        <img src="/openzoyi-bee.png" alt="OpenNzoyi" className="h-8 w-8" />
        <span className="text-lg font-bold tracking-tight">Open<span className="text-nzoyi-orange">Nzoyi</span></span>
      </Link>
      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-2">
        <div>
          <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-nzoyi-slate/70">Fonctions</p>
          <div className="space-y-0.5">
            {functions.map((it) => <Row key={it.href} it={it} active={isActive(it.href)} />)}
          </div>
        </div>
        <div>
          <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-nzoyi-slate/70">Système</p>
          <div className="space-y-0.5">
            {system.map((it) => <Row key={it.href} it={it} active={isActive(it.href)} />)}
          </div>
        </div>
      </nav>
      <div className="border-t border-nzoyi-border px-5 py-3 text-xs text-nzoyi-slate">
        OpenNzoyi · v1.0.0
      </div>
    </aside>
  );
}
