"use client";

import { use, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { api, Task, Finding, GraphData } from "@/lib/api";
import { StatusDot, SeverityBadge } from "@/components/ui";

const TaskGraph = dynamic(() => import("@/components/task-graph").then((m) => m.TaskGraph), {
  ssr: false,
  loading: () => <div className="p-8 text-sm text-nzoyi-slate">Chargement du graphe…</div>,
});

type Ev = { type: string; ts?: string; [k: string]: any };
const TABS = ["Sessions", "Graphe", "Findings", "Report"] as const;

export default function TaskDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Sessions");
  const [task, setTask] = useState<Task | null>(null);
  const [events, setEvents] = useState<Ev[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getTask(id).then(setTask).catch(() => {});
    const es = new EventSource(api.streamUrl(id));
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data) as Ev;
      if (ev.type === "eof") { es.close(); return; }
      setEvents((p) => [...p, ev]);
      if (ev.type === "status" && ev.status) setTask((t) => (t ? { ...t, status: ev.status } : t));
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [id]);

  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight); }, [events]);

  const toolCalls = events.filter((e) => e.type === "tool_call");
  const findings = toolCalls.reduce((n, e) => n + (e.findings || 0), 0);

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{task?.name ?? "Tâche"}</h1>
          <p className="font-mono text-sm text-nzoyi-slate">{task?.target}</p>
        </div>
        {task && <StatusDot status={task.status} />}
      </div>

      {/* Tab bar (façon ARTEX) */}
      <div className="flex gap-1 overflow-x-auto border-b border-nzoyi-border">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm transition ${
              tab === t ? "border-nzoyi-orange font-semibold text-nzoyi-ink"
                        : "border-transparent text-nzoyi-slate hover:text-nzoyi-ink"
            }`}>
            {t}
          </button>
        ))}
      </div>

      {tab === "Sessions" && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-1">
            <div className="card">
              <p className="mb-2 text-sm font-semibold">Workers</p>
              {toolCalls.length === 0 ? (
                <p className="text-sm text-nzoyi-slate">En attente…</p>
              ) : (
                <ul className="space-y-1.5 text-sm">
                  {toolCalls.map((e, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${e.ran ? "bg-nzoyi-success" : "bg-nzoyi-slate"}`} />
                      <span className="font-mono text-xs">#{i + 1}</span>
                      <span className="truncate">{e.phase} · {e.tool}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <div className="card lg:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold">Flux live</p>
              <span className="text-xs text-nzoyi-slate">{toolCalls.length} étapes · {findings} findings</span>
            </div>
            <div ref={logRef} className="max-h-[460px] overflow-y-auto rounded-xl bg-nzoyi-ink p-4 font-mono text-xs leading-relaxed text-white/90">
              {events.length === 0 && <p className="text-white/50">En attente d'événements…</p>}
              {events.map((e, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-white/40">{(e.ts || "").slice(11, 19)}</span>
                  <span className={e.type === "tool_call" ? "text-nzoyi-orange" : e.type === "status" ? "text-nzoyi-success" : "text-white/70"}>
                    {e.type === "tool_call"
                      ? `[${e.phase}] ${e.tool} → ${e.ran ? "run" : "skip"} ${e.reason || ""} (reward ${e.reward})`
                      : e.type === "status" ? `status: ${e.status}`
                      : e.type === "intent" ? `intent ${e.phase} ${e.target}` : JSON.stringify(e)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "Graphe" && <GraphTab id={id} />}
      {tab === "Findings" && <FindingsTab id={id} />}
      {tab === "Report" && <ReportTab id={id} />}
    </div>
  );
}

function GraphTab({ id }: { id: string }) {
  const [data, setData] = useState<GraphData | null>(null);
  useEffect(() => { api.graph(id).then(setData).catch(() => setData({ nodes: [], edges: [] })); }, [id]);
  if (!data) return <div className="card text-sm text-nzoyi-slate">Chargement…</div>;
  return (
    <div className="card">
      <p className="mb-3 text-sm font-semibold">Graphe d'exploration</p>
      <TaskGraph data={data} />
    </div>
  );
}

function FindingsTab({ id }: { id: string }) {
  const [findings, setFindings] = useState<Finding[]>([]);
  useEffect(() => { api.taskFindings(id).then(setFindings).catch(() => {}); }, [id]);
  return (
    <div className="card">
      {findings.length === 0 ? (
        <p className="py-8 text-center text-sm text-nzoyi-slate">Aucun finding (ou audit en cours).</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="text-left text-nzoyi-slate">
            <tr className="border-b border-nzoyi-border">
              <th className="pb-2 font-medium">Sévérité</th><th className="pb-2 font-medium">Titre</th>
              <th className="pb-2 font-medium">Preuve</th><th className="pb-2 font-medium">Outil</th>
            </tr>
          </thead>
          <tbody>
            {findings.map((f, i) => (
              <tr key={f.id} className={`border-b border-nzoyi-border/60 ${i % 2 ? "bg-nzoyi-bg/40" : ""}`}>
                <td className="py-2.5"><SeverityBadge severity={f.severity} /></td>
                <td className="py-2.5 font-medium">{f.title}</td>
                <td className="py-2.5 font-mono text-xs text-nzoyi-slate">{f.matched_at ?? "—"}</td>
                <td className="py-2.5">{f.tool ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ReportTab({ id }: { id: string }) {
  const [findings, setFindings] = useState<Finding[]>([]);
  useEffect(() => { api.taskFindings(id).then(setFindings).catch(() => {}); }, [id]);
  function exportJson() {
    const blob = new Blob([JSON.stringify(findings, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `report_${id}.json`;
    a.click();
  }
  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">Rapport d'audit</p>
        <button className="btn-primary" onClick={exportJson} disabled={!findings.length}>Export JSON</button>
      </div>
      <p className="text-sm text-nzoyi-slate">{findings.length} finding(s) exportable(s).</p>
    </div>
  );
}
