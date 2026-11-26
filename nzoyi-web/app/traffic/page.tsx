"use client";

import { useEffect, useMemo, useState } from "react";
import { api, Flow } from "@/lib/api";

const METHOD_CLS: Record<string, string> = {
  GET: "bg-nzoyi-ink text-white",
  POST: "bg-nzoyi-orange text-white",
  PUT: "bg-nzoyi-amber text-white",
  DELETE: "bg-nzoyi-danger text-white",
};

function statusCls(s?: number) {
  if (!s) return "text-nzoyi-slate";
  if (s < 300) return "text-nzoyi-success";
  if (s < 400) return "text-blue-500";
  if (s < 500) return "text-nzoyi-amber";
  return "text-nzoyi-danger";
}

export default function TrafficPage() {
  const [flows, setFlows] = useState<Flow[]>([]);
  const [port, setPort] = useState(8788);
  const [q, setQ] = useState("");
  const [method, setMethod] = useState("all");

  const load = () =>
    api.traffic().then((r) => { setFlows(r.flows); setPort(r.proxy_port); }).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);

  const filtered = useMemo(
    () => flows.filter(
      (f) => (method === "all" || f.request.method === method) &&
             ((f.request.url ?? "").toLowerCase().includes(q.toLowerCase()))
    ),
    [flows, q, method]
  );

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trafic</h1>
          <p className="text-sm text-nzoyi-slate">
            Proxy d'enregistrement global — tout le trafic HTTP · port {port}
          </p>
        </div>
        <span className="badge bg-nzoyi-success/10 text-nzoyi-success">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" /> Recording
        </span>
      </div>

      <div className="card">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <input className="input max-w-xs" placeholder="Rechercher une URL"
                 value={q} onChange={(e) => setQ(e.target.value)} />
          <select className="input max-w-[160px]" value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="all">Toutes méthodes</option>
            {["GET", "POST", "PUT", "DELETE"].map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <span className="ml-auto text-sm text-nzoyi-slate">{filtered.length} flux</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-nzoyi-slate">
              <tr className="border-b border-nzoyi-border">
                <th className="pb-2 font-medium">Heure</th>
                <th className="pb-2 font-medium">Méthode</th>
                <th className="pb-2 font-medium">URL</th>
                <th className="pb-2 font-medium">Statut</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={4} className="py-10 text-center text-nzoyi-slate">
                  Aucun flux capturé. Le proxy MITM (port {port}) enregistre le trafic des outils HTTP pendant un audit.
                </td></tr>
              )}
              {filtered.map((f, i) => (
                <tr key={f.id} className={`border-b border-nzoyi-border/60 ${i % 2 ? "bg-nzoyi-bg/40" : ""}`}>
                  <td className="py-2.5 font-mono text-xs text-nzoyi-slate">{f.captured_at.slice(11, 19)}</td>
                  <td className="py-2.5">
                    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${METHOD_CLS[f.request.method ?? "GET"] ?? "bg-nzoyi-slate text-white"}`}>
                      {f.request.method}
                    </span>
                  </td>
                  <td className="py-2.5 font-mono text-xs">{f.request.url}</td>
                  <td className={`py-2.5 font-mono text-xs font-semibold ${statusCls(f.response.status)}`}>
                    {f.response.status ?? "—"}
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
