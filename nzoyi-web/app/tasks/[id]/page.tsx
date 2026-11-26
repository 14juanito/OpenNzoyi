"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, Task } from "@/lib/api";
import { StatusDot } from "@/components/ui";

type Ev = { type: string; ts?: string; [k: string]: any };

export default function TaskLive({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [task, setTask] = useState<Task | null>(null);
  const [events, setEvents] = useState<Ev[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getTask(id).then(setTask).catch(() => {});
    const es = new EventSource(api.streamUrl(id));
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data) as Ev;
      if (ev.type === "eof") { es.close(); return; }
      setEvents((prev) => [...prev, ev]);
      if (ev.type === "status" && ev.status) {
        setTask((t) => (t ? { ...t, status: ev.status } : t));
      }
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [id]);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [events]);

  const toolCalls = events.filter((e) => e.type === "tool_call");
  const findings = toolCalls.reduce((n, e) => n + (e.findings || 0), 0);
  const ran = toolCalls.filter((e) => e.ran).length;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{task?.name ?? "Tâche"}</h1>
          <p className="font-mono text-sm text-nzoyi-slate">{task?.target}</p>
        </div>
        <div className="flex items-center gap-3">
          {task && <StatusDot status={task.status} />}
          <Link href={`/tasks/${id}/findings`} className="btn-ghost">Findings</Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Counter label="Étapes" value={toolCalls.length} />
        <Counter label="Exécutées" value={ran} />
        <Counter label="Findings" value={findings} accent />
        <Counter label="Profil" value={task?.profile ?? "—"} />
      </div>

      <div className="card">
        <h2 className="mb-3 font-semibold">Flux live</h2>
        <div ref={logRef} className="max-h-96 overflow-y-auto rounded-xl bg-nzoyi-ink p-4 font-mono text-xs leading-relaxed text-white/90">
          {events.length === 0 && <p className="text-white/50">En attente d'événements…</p>}
          {events.map((e, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-white/40">{(e.ts || "").slice(11, 19)}</span>
              <span className={
                e.type === "tool_call" ? "text-nzoyi-orange"
                : e.type === "status" ? "text-nzoyi-success" : "text-white/70"
              }>
                {e.type === "tool_call"
                  ? `[${e.phase}] ${e.tool} → ${e.ran ? "run" : "skip"} ${e.reason || ""} (reward ${e.reward})`
                  : e.type === "status" ? `status: ${e.status}`
                  : e.type === "intent" ? `intent ${e.phase} ${e.target}`
                  : JSON.stringify(e)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Counter({ label, value, accent }: { label: string; value: any; accent?: boolean }) {
  return (
    <div className={`card ${accent ? "bg-nzoyi-orange text-white border-nzoyi-orange" : ""}`}>
      <p className={`text-xs ${accent ? "text-white/80" : "text-nzoyi-slate"}`}>{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}
