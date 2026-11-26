"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api, Finding } from "@/lib/api";
import { SeverityBadge } from "@/components/ui";

export default function Findings({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.findings(id).then((f) => { setFindings(f); setLoading(false); }).catch(() => setLoading(false));
  }, [id]);

  function exportJson() {
    const blob = new Blob([JSON.stringify(findings, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `findings_${id}.json`;
    a.click();
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Findings</h1>
          <p className="text-sm text-nzoyi-slate">{findings.length} résultat(s)</p>
        </div>
        <div className="flex gap-3">
          <Link href={`/tasks/${id}`} className="btn-ghost">← Live</Link>
          <button className="btn-primary" onClick={exportJson} disabled={!findings.length}>
            Export JSON
          </button>
        </div>
      </div>

      <div className="card">
        {loading ? (
          <p className="py-8 text-center text-sm text-nzoyi-slate">Chargement…</p>
        ) : findings.length === 0 ? (
          <p className="py-8 text-center text-sm text-nzoyi-slate">
            Aucun finding (ou audit encore en cours).
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-nzoyi-slate">
                <tr className="border-b border-nzoyi-border">
                  <th className="pb-2 font-medium">Sévérité</th>
                  <th className="pb-2 font-medium">Titre</th>
                  <th className="pb-2 font-medium">Preuve</th>
                  <th className="pb-2 font-medium">Outil</th>
                  <th className="pb-2 font-medium">Statut</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {findings.map((f, i) => (
                  <tr key={f.id} className={`border-b border-nzoyi-border/60 ${i % 2 ? "bg-nzoyi-bg/40" : ""}`}>
                    <td className="py-2.5"><SeverityBadge severity={f.severity} /></td>
                    <td className="py-2.5 font-medium">{f.title}</td>
                    <td className="py-2.5 font-mono text-xs text-nzoyi-slate">{f.matched_at ?? "—"}</td>
                    <td className="py-2.5">{f.tool ?? "—"}</td>
                    <td className="py-2.5 text-nzoyi-slate">{f.status}</td>
                    <td className="py-2.5 text-right">
                      <button className="text-xs font-medium text-nzoyi-orange hover:underline"
                              onClick={() => api.findings(id).then(setFindings)}>
                        Retest
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
