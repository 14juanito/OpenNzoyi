"use client";

import { useEffect, useState } from "react";
import { api, AttackCoverage } from "@/lib/api";

const TACTIC_LABEL: Record<string, string> = {
  "reconnaissance": "Reconnaissance",
  "discovery": "Découverte",
  "initial-access": "Accès initial",
  "execution": "Exécution",
  "privilege-escalation": "Élévation de privilèges",
  "credential-access": "Accès aux identifiants",
  "lateral-movement": "Mouvement latéral",
  "command-and-control": "C2",
  "defense-evasion": "Évasion défensive",
};

function cellCls(count: number) {
  if (count === 0) return "bg-nzoyi-bg text-nzoyi-slate/60 border-nzoyi-border";
  if (count >= 3) return "bg-nzoyi-orange text-white border-nzoyi-orange";
  if (count === 2) return "bg-nzoyi-orange/50 text-nzoyi-ink border-nzoyi-orange/50";
  return "bg-nzoyi-orange/20 text-nzoyi-ink border-nzoyi-orange/30";
}

export default function AttackPage() {
  const [cov, setCov] = useState<AttackCoverage | null>(null);
  const load = () => api.attackCoverage().then(setCov).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, []);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Couverture MITRE ATT&CK</h1>
        <p className="text-sm text-nzoyi-slate">
          Techniques exercées par les outils et prouvées par les findings
          {cov && <> · <b className="text-nzoyi-ink">{cov.techniques_exercised}</b> / {cov.techniques_total} techniques</>}
        </p>
      </div>

      <div className="card overflow-x-auto">
        <div className="flex gap-3" style={{ minWidth: "900px" }}>
          {cov?.tactics.map((tac) => (
            <div key={tac} className="flex-1">
              <div className="mb-2 rounded-lg bg-nzoyi-ink px-2 py-1.5 text-center text-[11px] font-semibold text-white">
                {TACTIC_LABEL[tac] ?? tac}
              </div>
              <div className="space-y-1.5">
                {(cov.by_tactic[tac] ?? []).map((t) => (
                  <div key={t.id} title={`${t.id} · ${t.name} · ${t.count}×`}
                       className={`rounded-lg border px-2 py-1.5 text-center ${cellCls(t.count)}`}>
                    <p className="font-mono text-[10px] font-semibold">{t.id}</p>
                    <p className="truncate text-[10px] leading-tight">{t.name}</p>
                    {t.count > 0 && <p className="text-[9px] font-bold">{t.count}×</p>}
                  </div>
                ))}
                {(cov.by_tactic[tac] ?? []).length === 0 && (
                  <p className="text-center text-[10px] text-nzoyi-slate/50">—</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs text-nzoyi-slate">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded border border-nzoyi-border bg-nzoyi-bg" /> non exercée</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-nzoyi-orange/20" /> 1×</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-nzoyi-orange/50" /> 2×</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-nzoyi-orange" /> 3×+</span>
      </div>
    </div>
  );
}
