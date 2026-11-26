"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { api, ApprovalRecord } from "@/lib/api";

const STATUS_CLS: Record<string, string> = {
  allowed: "bg-nzoyi-ink text-white",
  denied: "bg-nzoyi-danger/10 text-nzoyi-danger",
  pending: "bg-nzoyi-amber/10 text-nzoyi-amber",
};

function Badge({ status }: { status: string }) {
  const label = status === "allowed" ? "Autorisé" : status === "denied" ? "Refusé" : "En attente";
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_CLS[status]}`}>{label}</span>;
}

function fmt(ts: string | null) {
  return ts ? ts.slice(5, 16).replace("T", " ") : "—";
}

export default function ApprovalsPage() {
  const [records, setRecords] = useState<ApprovalRecord[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [fStatus, setFStatus] = useState("all");
  const [fSource, setFSource] = useState("all");

  const load = () => api.approvalRecords().then((r) => setRecords(r.records)).catch(() => setRecords([]));
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);

  const pending = records.filter((r) => r.status === "pending");
  const filtered = useMemo(() => records.filter(
    (r) => (fStatus === "all" || r.status === fStatus) &&
           (fSource === "all" || r.decision_source === fSource)
  ), [records, fStatus, fSource]);

  async function decide(seq: number, status: "allowed" | "denied") {
    await api.decideApproval(seq, status).catch(() => {});
    load();
  }

  const Table = ({ rows, pendingMode }: { rows: ApprovalRecord[]; pendingMode?: boolean }) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-nzoyi-slate">
          <tr className="border-b border-nzoyi-border">
            <th className="pb-2 font-medium">#</th>
            <th className="pb-2 font-medium">Outil</th>
            <th className="pb-2 font-medium">Source</th>
            <th className="pb-2 font-medium">Règle / raison</th>
            <th className="pb-2 font-medium">Statut</th>
            <th className="pb-2 font-medium">Décidé par</th>
            <th className="pb-2 font-medium">Demandé</th>
            <th className="pb-2 font-medium">Décidé</th>
            {pendingMode && <th className="pb-2 font-medium text-right">Action</th>}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={pendingMode ? 9 : 8} className="py-8 text-center text-nzoyi-slate">
              {pendingMode ? "Aucune approbation en attente." :
                "Aucun enregistrement. Les décisions d'interception (actions destructrices / règles) apparaissent ici."}
            </td></tr>
          )}
          {rows.map((r) => (
            <Fragment key={r.seq}>
              <tr className="border-b border-nzoyi-border/60 hover:bg-nzoyi-bg/40">
                <td className="py-2.5 font-mono text-xs text-nzoyi-slate">{r.seq}</td>
                <td className="py-2.5 font-mono text-xs">{r.tool}</td>
                <td className="py-2.5">
                  <span className="text-nzoyi-ink">{r.task_name}</span>
                  <span className="ml-1 text-xs text-nzoyi-slate">{r.source}</span>
                </td>
                <td className="py-2.5">
                  <button onClick={() => setExpanded(expanded === r.seq ? null : r.seq)}
                          className="max-w-[220px] truncate text-left text-nzoyi-slate hover:text-nzoyi-ink">
                    {r.decision_source === "rule" ? "règle" : "politique"} · {r.matched_rule}
                  </button>
                </td>
                <td className="py-2.5"><Badge status={r.status} /></td>
                <td className="py-2.5 text-xs text-nzoyi-slate">{r.decided_by ?? "—"}</td>
                <td className="py-2.5 font-mono text-xs text-nzoyi-slate">{fmt(r.requested_at)}</td>
                <td className="py-2.5 font-mono text-xs text-nzoyi-slate">{fmt(r.decided_at)}</td>
                {pendingMode && (
                  <td className="py-2.5">
                    <div className="flex justify-end gap-2">
                      <button onClick={() => decide(r.seq, "allowed")} className="rounded-lg bg-nzoyi-ink px-2.5 py-1 text-xs text-white">Autoriser</button>
                      <button onClick={() => decide(r.seq, "denied")} className="rounded-lg border border-nzoyi-danger px-2.5 py-1 text-xs text-nzoyi-danger">Refuser</button>
                    </div>
                  </td>
                )}
              </tr>
              {expanded === r.seq && (
                <tr key={`${r.seq}-exp`}>
                  <td colSpan={pendingMode ? 9 : 8} className="bg-nzoyi-bg/60 px-4 py-3">
                    <p className="mb-1 text-xs font-semibold text-nzoyi-slate">Arguments</p>
                    <pre className="overflow-x-auto rounded-lg bg-nzoyi-ink p-3 font-mono text-xs text-white/90">
{JSON.stringify(r.arguments, null, 2)}</pre>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">Approbations</h1>
        {pending.length > 0 && (
          <span className="rounded-full bg-nzoyi-amber/10 px-2.5 py-0.5 text-xs font-medium text-nzoyi-amber">
            {pending.length} en attente
          </span>
        )}
      </div>
      <p className="-mt-3 text-sm text-nzoyi-slate">
        Journal des décisions d'interception. En mode autonome, les actions
        destructrices sont autorisées et journalisées ; en mode semi-autonome,
        elles attendent une décision humaine.
      </p>

      <div className="card">
        <div className="mb-4 flex flex-wrap gap-3">
          <select className="input max-w-[180px]" value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
            <option value="all">Tous les statuts</option>
            <option value="allowed">Autorisé</option>
            <option value="denied">Refusé</option>
            <option value="pending">En attente</option>
          </select>
          <select className="input max-w-[200px]" value={fSource} onChange={(e) => setFSource(e.target.value)}>
            <option value="all">Toutes sources</option>
            <option value="rule">Règle explicite</option>
            <option value="default">Politique par défaut</option>
          </select>
        </div>
      </div>

      {pending.length > 0 && (
        <div className="card border-nzoyi-amber/40">
          <p className="mb-3 text-sm font-semibold">En attente ({pending.length}) — autoriser ou refuser</p>
          <Table rows={pending} pendingMode />
        </div>
      )}

      <div className="card">
        <p className="mb-3 text-sm font-semibold">Tous les enregistrements ({filtered.length})</p>
        <Table rows={filtered} />
      </div>
    </div>
  );
}
