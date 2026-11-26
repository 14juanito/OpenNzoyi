"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Task } from "@/lib/api";
import { StatCard, StatusDot } from "@/components/ui";

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .listTasks()
      .then((t) => {
        setTasks(t);
        setOnline(true);
      })
      .catch(() => setOnline(false));
  }, []);

  const active = tasks.filter((t) => t.status === "running").length;
  const done = tasks.filter((t) => t.status === "done").length;
  const bars = [40, 65, 30, 80, 55, 70, 45, 60];

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Bonjour, Opérateur</h1>
        <p className="text-sm text-nzoyi-slate">
          Supervisez vos audits, suivez les findings et l'état du système.
        </p>
      </div>

      {/* Cartes de résumé */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="card xl:row-span-1">
          <p className="text-sm text-nzoyi-slate">Total Findings</p>
          <p className="mt-2 text-3xl font-bold">{tasks.length ? "—" : 0}</p>
          <div className="mt-4 flex items-end gap-1">
            {bars.map((h, i) => (
              <div key={i} className="flex-1 rounded-sm bg-nzoyi-orange/20"
                   style={{ height: `${h}px` }}>
                <div className="h-1 w-full rounded-sm bg-nzoyi-orange" />
              </div>
            ))}
          </div>
        </div>

        <StatCard label="Tâches actives" value={active} hint="en cours d'exécution" accent />
        <StatCard label="Tâches terminées" value={done} hint="audits complétés" />
        <StatCard label="Taux de détection" value="—" hint="alertes IDS / actions">
          <div className="mt-3 flex items-end gap-1">
            {bars.slice(0, 6).map((h, i) => (
              <div key={i} className="flex-1 rounded-sm bg-nzoyi-ink/10"
                   style={{ height: `${h / 2}px` }} />
            ))}
          </div>
        </StatCard>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Activités récentes */}
        <div className="card lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Tâches récentes</h2>
            <Link href="/tasks/new" className="btn-primary">
              <span className="text-lg leading-none">+</span> Nouvelle tâche
            </Link>
          </div>
          {tasks.length === 0 ? (
            <p className="py-8 text-center text-sm text-nzoyi-slate">
              Aucune tâche. Créez un audit pour commencer.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-nzoyi-slate">
                  <tr className="border-b border-nzoyi-border">
                    <th className="pb-2 font-medium">Tâche</th>
                    <th className="pb-2 font-medium">Cible</th>
                    <th className="pb-2 font-medium">Profil</th>
                    <th className="pb-2 font-medium">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.slice(0, 8).map((t, i) => (
                    <tr key={t.id}
                        className={`border-b border-nzoyi-border/60 ${i % 2 ? "bg-nzoyi-bg/40" : ""}`}>
                      <td className="py-2.5">
                        <Link href={`/tasks/${t.id}`} className="font-medium hover:text-nzoyi-orange">
                          {t.name}
                        </Link>
                      </td>
                      <td className="py-2.5 font-mono text-xs text-nzoyi-slate">{t.target}</td>
                      <td className="py-2.5">{t.profile}</td>
                      <td className="py-2.5"><StatusDot status={t.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* État système */}
        <div className="card">
          <h2 className="mb-4 font-semibold">État du système</h2>
          <ul className="space-y-3 text-sm">
            <SystemRow label="API nzoyi-api" ok={online} />
            <SystemRow label="Microservice RL" ok={online} />
            <SystemRow label="PostgreSQL" ok={online} />
            <SystemRow label="Proxy MITM (8788)" ok={online} />
          </ul>
        </div>
      </div>
    </div>
  );
}

function SystemRow({ label, ok }: { label: string; ok: boolean | null }) {
  const color = ok === null ? "bg-nzoyi-slate" : ok ? "bg-nzoyi-success" : "bg-nzoyi-danger";
  const text = ok === null ? "…" : ok ? "opérationnel" : "injoignable";
  return (
    <li className="flex items-center justify-between">
      <span className="text-nzoyi-slate">{label}</span>
      <span className="flex items-center gap-2 font-medium">
        <span className={`h-2 w-2 rounded-full ${color}`} /> {text}
      </span>
    </li>
  );
}
