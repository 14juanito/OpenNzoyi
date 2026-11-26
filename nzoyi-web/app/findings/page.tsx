"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, Finding, FindingsAgg, Severity } from "@/lib/api";
import { SeverityBadge } from "@/components/ui";

const SEV_TABS: (Severity | "all")[] = ["all", "critical", "high", "medium", "low"];

export default function FindingsPage() {
  const [agg, setAgg] = useState<FindingsAgg | null>(null);
  const [q, setQ] = useState("");
  const [sev, setSev] = useState<Severity | "all">("all");
  const [dedup, setDedup] = useState(false);

  const load = () => api.allFindings(dedup).then(setAgg).catch(() => setAgg({ total: 0, pending: 0, by_severity: {} as any, findings: [] }));
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [dedup]);

  const findings = useMemo(() => {
    const items = agg?.findings ?? [];
    return items.filter(
      (f) => (sev === "all" || f.severity === sev) &&
             (f.title?.toLowerCase().includes(q.toLowerCase()) ?? true)
    );
  }, [agg, q, sev]);

  const bs = agg?.by_severity;
  const cards = [
    { label: "Total", value: agg?.total ?? 0, cls: "text-nzoyi-ink" },
    { label: "En attente", value: agg?.pending ?? 0, cls: "text-nzoyi-amber" },
    { label: "Critical", value: bs?.critical ?? 0, cls: "text-nzoyi-danger" },
    { label: "High", value: bs?.high ?? 0, cls: "text-nzoyi-orange" },
    { label: "Medium", value: bs?.medium ?? 0, cls: "text-nzoyi-amber" },
    { label: "Low", value: bs?.low ?? 0, cls: "text-nzoyi-slate" },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Findings</h1>
        <p className="text-sm text-nzoyi-slate">Vue des vulnérabilités, toutes tâches confondues</p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        {cards.map((c) => (
          <div key={c.label} className="card py-4">
            <p className="text-xs text-nzoyi-slate">{c.label}</p>
            <p className={`mt-1 text-2xl font-bold ${c.cls}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <input className="input max-w-xs" placeholder="Rechercher un finding"
                 value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="flex gap-1 rounded-xl border border-nzoyi-border p-1">
            {SEV_TABS.map((s) => (
              <button key={s} onClick={() => setSev(s)}
                className={`rounded-lg px-3 py-1 text-sm capitalize transition ${
                  sev === s ? "bg-nzoyi-orange/10 text-nzoyi-orange font-medium" : "text-nzoyi-slate hover:text-nzoyi-ink"
                }`}>
                {s === "all" ? "Tous" : s}
              </button>
            ))}
          </div>
          <label className="ml-auto flex cursor-pointer items-center gap-2 text-sm text-nzoyi-slate">
            <input type="checkbox" checked={dedup} onChange={(e) => setDedup(e.target.checked)}
                   className="accent-nzoyi-orange" />
            Dédupliquer
          </label>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-nzoyi-slate">
              <tr className="border-b border-nzoyi-border">
                <th className="pb-2 font-medium">Sévérité</th>
                <th className="pb-2 font-medium">Vulnérabilité</th>
                <th className="pb-2 font-medium">Preuve</th>
                <th className="pb-2 font-medium">Statut</th>
                <th className="pb-2 font-medium">Tâche</th>
                <th className="pb-2 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {findings.length === 0 && (
                <tr><td colSpan={6} className="py-10 text-center text-nzoyi-slate">
                  Aucun finding pour le moment.
                </td></tr>
              )}
              {findings.map((f, i) => (
                <tr key={f.id} className={`border-b border-nzoyi-border/60 ${i % 2 ? "bg-nzoyi-bg/40" : ""}`}>
                  <td className="py-3"><SeverityBadge severity={f.severity} /></td>
                  <td className="py-3 font-medium">
                    {f.title}
                    {dedup && f.instances && f.instances > 1 && (
                      <span className="ml-2 rounded-full bg-nzoyi-ink/10 px-2 py-0.5 text-[11px] font-semibold text-nzoyi-slate">
                        ×{f.instances}
                      </span>
                    )}
                    {f.attack && f.attack.length > 0 && (
                      <span className="ml-2 inline-flex gap-1 align-middle">
                        {f.attack.map((a) => (
                          <span key={a.id} title={a.name}
                                className="rounded bg-nzoyi-ink/5 px-1.5 py-0.5 font-mono text-[10px] text-nzoyi-slate">
                            {a.id}
                          </span>
                        ))}
                      </span>
                    )}
                  </td>
                  <td className="py-3 font-mono text-xs text-nzoyi-slate">{f.matched_at ?? "—"}</td>
                  <td className="py-3 text-nzoyi-slate">{f.status}</td>
                  <td className="py-3">
                    {f.task_id ? (
                      <Link href={`/tasks/${f.task_id}`} className="text-nzoyi-slate hover:text-nzoyi-orange">
                        {f.task_name}
                      </Link>
                    ) : "—"}
                  </td>
                  <td className="py-3 text-right">
                    <button className="text-xs font-medium text-nzoyi-orange hover:underline">Retest</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
