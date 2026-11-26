"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Task } from "@/lib/api";
import { StatusDot } from "@/components/ui";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");

  const load = () => api.listTasks().then(setTasks).catch(() => {});
  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  const filtered = tasks.filter(
    (t) =>
      (status === "all" || t.status === status) &&
      (t.name.toLowerCase().includes(q.toLowerCase()) ||
        t.target.toLowerCase().includes(q.toLowerCase()) ||
        t.id.includes(q))
  );

  async function remove(id: string) {
    await api.deleteTask(id).catch(() => {});
    load();
  }

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tâches</h1>
          <p className="text-sm text-nzoyi-slate">{filtered.length} tâche(s)</p>
        </div>
        <Link href="/tasks/new" className="btn-primary">
          <span className="text-lg leading-none">+</span> Nouvelle tâche
        </Link>
      </div>

      <div className="card">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <input className="input max-w-xs" placeholder="Rechercher nom / cible / ID"
                 value={q} onChange={(e) => setQ(e.target.value)} />
          <select className="input max-w-[180px]" value={status}
                  onChange={(e) => setStatus(e.target.value)}>
            <option value="all">Tous les statuts</option>
            <option value="running">Running</option>
            <option value="done">Done</option>
            <option value="failed">Failed</option>
            <option value="killed">Killed</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-nzoyi-slate">
              <tr className="border-b border-nzoyi-border">
                <th className="pb-2 font-medium">ID</th>
                <th className="pb-2 font-medium">Nom</th>
                <th className="pb-2 font-medium">Cible</th>
                <th className="pb-2 font-medium">Profil</th>
                <th className="pb-2 font-medium">Statut</th>
                <th className="pb-2 font-medium">Étapes</th>
                <th className="pb-2 font-medium">Findings (C/H/M/L)</th>
                <th className="pb-2 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={8} className="py-10 text-center text-nzoyi-slate">
                  Aucune tâche. Créez un audit pour commencer.
                </td></tr>
              )}
              {filtered.map((t, i) => {
                const sev = t.findings_by_severity;
                return (
                  <tr key={t.id} className={`border-b border-nzoyi-border/60 ${i % 2 ? "bg-nzoyi-bg/40" : ""}`}>
                    <td className="py-3 font-mono text-xs text-nzoyi-slate">{t.id.slice(0, 8)}</td>
                    <td className="py-3">
                      <Link href={`/tasks/${t.id}`} className="font-medium hover:text-nzoyi-orange">{t.name}</Link>
                    </td>
                    <td className="py-3 font-mono text-xs text-nzoyi-slate">{t.target}</td>
                    <td className="py-3">{t.profile}</td>
                    <td className="py-3"><StatusDot status={t.status} /></td>
                    <td className="py-3 text-nzoyi-slate">{t.steps_ran ?? 0}/{t.steps ?? 0}</td>
                    <td className="py-3">
                      {sev ? (
                        <span className="font-mono text-xs">
                          <span className="text-nzoyi-danger">{sev.critical}</span>/
                          <span className="text-nzoyi-orange">{sev.high}</span>/
                          <span className="text-nzoyi-amber">{sev.medium}</span>/
                          <span className="text-nzoyi-slate">{sev.low}</span>
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-3">
                      <div className="flex items-center justify-end gap-3">
                        <Link href={`/tasks/${t.id}`} className="text-nzoyi-slate hover:text-nzoyi-ink" title="Ouvrir">
                          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8}>
                            <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" /><circle cx="12" cy="12" r="3" />
                          </svg>
                        </Link>
                        <button onClick={() => remove(t.id)} className="text-nzoyi-slate hover:text-nzoyi-danger" title="Supprimer">
                          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8}>
                            <path d="M3 6h18M8 6V4h8v2m-9 0v14h10V6" strokeLinecap="round" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
