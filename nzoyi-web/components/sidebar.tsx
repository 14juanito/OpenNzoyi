"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Dashboard", icon: "grid" },
  { href: "/tasks/new", label: "Nouvelle tâche", icon: "plus" },
  { href: "/tasks", label: "Tâches", icon: "list" },
  { href: "/graph", label: "Graphe", icon: "share" },
  { href: "/traffic", label: "Trafic", icon: "activity" },
  { href: "/settings", label: "Paramètres", icon: "settings" },
];

const paths: Record<string, string> = {
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
  plus: "M12 5v14M5 12h14",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  share: "M18 8a3 3 0 10-2.83-4M6 15a3 3 0 100 6 3 3 0 000-6zm12 0a3 3 0 100 6 3 3 0 000-6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4",
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  settings: "M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.6a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9c.14.63.67 1.09 1.31 1.09H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z",
};

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-16 flex-col items-center gap-2 border-r border-nzoyi-border bg-white py-5 md:w-20">
      <Link href="/" className="mb-4">
        <img src="/openzoyi-bee.png" alt="OpenZoyi" className="h-9 w-9" />
      </Link>
      {items.map((it) => {
        const active = pathname === it.href;
        return (
          <Link
            key={it.href}
            href={it.href}
            title={it.label}
            className={`flex h-11 w-11 items-center justify-center rounded-xl transition ${
              active
                ? "bg-nzoyi-orange/10 text-nzoyi-orange"
                : "text-nzoyi-slate hover:bg-nzoyi-bg hover:text-nzoyi-ink"
            }`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
                 strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
              <path d={paths[it.icon]} />
            </svg>
          </Link>
        );
      })}
    </aside>
  );
}
