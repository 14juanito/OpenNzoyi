"use client";
import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";

export default function ApprovalsPage() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    fetch(`${API_URL}/api/approvals`).then((r) => r.json()).then(setItems).catch(() => {});
  }, []);
  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Approbations</h1>
        <p className="text-sm text-nzoyi-slate">
          Actions destructrices en attente de validation humaine (mode semi-autonome)
        </p>
      </div>
      <div className="card">
        {items.length === 0 ? (
          <p className="py-8 text-center text-sm text-nzoyi-slate">
            Aucune approbation en attente. En mode autonome, les actions
            destructrices sont exécutées et journalisées (interception gate).
          </p>
        ) : (
          <ul className="divide-y divide-nzoyi-border/60">
            {items.map((a, i) => (
              <li key={i} className="flex items-center justify-between py-3 text-sm">
                <span className="font-mono text-xs">{JSON.stringify(a.tool_call)}</span>
                <div className="flex gap-2">
                  <button className="btn-primary">Approuver</button>
                  <button className="btn-ghost">Refuser</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
