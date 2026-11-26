"use client";

import { useEffect, useState } from "react";
import { api, GlobalTelemetry, Telemetry } from "@/lib/api";

function RewardBars({ series }: { series: Telemetry["reward_series"] }) {
  if (!series.length) return <p className="text-xs text-nzoyi-slate">Aucune étape.</p>;
  const max = Math.max(1, ...series.map((s) => Math.abs(s.reward)));
  return (
    <div className="flex h-20 items-end gap-1">
      {series.map((s) => {
        const h = Math.max(4, (Math.abs(s.reward) / max) * 72);
        const pos = s.reward >= 0;
        return (
          <div key={s.step} title={`#${s.step} ${s.phase}/${s.tool} · reward ${s.reward}`}
               className="flex flex-1 flex-col justify-end">
            <div className={`rounded-sm ${pos ? "bg-nzoyi-orange" : "bg-nzoyi-danger"}`}
                 style={{ height: `${h}px` }} />
          </div>
        );
      })}
    </div>
  );
}

function stealthCls(s: number) {
  return s >= 0.8 ? "text-nzoyi-success" : s >= 0.5 ? "text-nzoyi-amber" : "text-nzoyi-danger";
}

export default function TelemetryPage() {
  const [data, setData] = useState<GlobalTelemetry | null>(null);
  const [tasks, setTasks] = useState<Record<string, string>>({});
  const load = () => api.telemetry().then(setData).catch(() => {});
  useEffect(() => {
    load();
    api.listTasks().then((ts) => setTasks(Object.fromEntries(ts.map((t) => [t.id, t.name])))).catch(() => {});
    const t = setInterval(load, 4000); return () => clearInterval(t);
  }, []);

  const withSteps = (data?.per_task ?? []).filter((t) => t.steps > 0);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Télémétrie RL &amp; furtivité</h1>
        <p className="text-sm text-nzoyi-slate">
          Récompense d'apprentissage, détection prédite vs observée, score de furtivité.
          Le cœur d'évasion d'OpenNzoyi — jamais de LLM dans cette boucle.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="card py-4">
          <p className="text-xs text-nzoyi-slate">Score furtivité moyen</p>
          <p className={`mt-1 text-2xl font-bold ${data?.avg_stealth_score != null ? stealthCls(data.avg_stealth_score) : ""}`}>
            {data?.avg_stealth_score ?? "—"}
          </p>
        </div>
        <div className="card py-4"><p className="text-xs text-nzoyi-slate">Étapes totales</p><p className="mt-1 text-2xl font-bold">{data?.total_steps ?? 0}</p></div>
        <div className="card py-4"><p className="text-xs text-nzoyi-slate">Alertes IDS</p><p className="mt-1 text-2xl font-bold">{data?.total_alerts ?? 0}</p></div>
        <div className="card py-4"><p className="text-xs text-nzoyi-slate">ε (exploration)</p><p className="mt-1 text-2xl font-bold">{withSteps[0]?.epsilon ?? "—"}</p></div>
      </div>

      {withSteps.length === 0 ? (
        <div className="card py-10 text-center text-sm text-nzoyi-slate">
          Aucune donnée de télémétrie. Lancez un audit pour alimenter la courbe de
          récompense et la détection prédite vs observée.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {withSteps.map((t) => (
            <div key={t.task_id} className="card">
              <div className="mb-3 flex items-center justify-between">
                <p className="font-semibold">{tasks[t.task_id] ?? t.task_id.slice(0, 8)}</p>
                <span className={`text-sm font-bold ${stealthCls(t.stealth_score)}`}>
                  furtivité {t.stealth_score}
                </span>
              </div>
              <p className="mb-1 text-xs text-nzoyi-slate">Récompense par étape</p>
              <RewardBars series={t.reward_series} />
              <p className="mb-1 mt-4 text-xs text-nzoyi-slate">Détection prédite vs observée</p>
              <div className="space-y-1.5">
                {t.detection.map((d) => (
                  <div key={d.tool} className="flex items-center gap-2 text-xs">
                    <span className="w-24 shrink-0 font-mono">{d.tool}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-nzoyi-bg">
                      <div className="h-full bg-nzoyi-orange" style={{ width: `${d.predicted * 100}%` }} />
                    </div>
                    <span className="w-20 shrink-0 text-right text-nzoyi-slate">
                      {Math.round(d.predicted * 100)}% / {d.observed_alerts}
                    </span>
                  </div>
                ))}
                {t.detection.length === 0 && <p className="text-xs text-nzoyi-slate">—</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
