"use client";

import { useEffect, useRef, useState } from "react";
import { api, Conversation, ChatMsg, Task } from "@/lib/api";

const PHASES = ["recon", "vuln", "ad_enum", "linux", "lateral", "post"];

export default function ChatPage() {
  const [convs, setConvs] = useState<Conversation[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [draft, setDraft] = useState("");
  const [hintPhase, setHintPhase] = useState("vuln");
  const [busy, setBusy] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

  const loadConvs = () => api.listConversations().then(setConvs).catch(() => {});
  useEffect(() => { loadConvs(); api.listTasks().then(setTasks).catch(() => {}); }, []);
  useEffect(() => { threadRef.current?.scrollTo(0, threadRef.current.scrollHeight); }, [active]);

  async function newConversation(taskId?: string) {
    const title = taskId ? tasks.find((t) => t.id === taskId)?.name ?? "Tâche" : "Discussion générale";
    const c = await api.createConversation({ title, task_id: taskId ?? null });
    await loadConvs();
    setActive(c);
  }

  async function open(c: Conversation) {
    const full = await api.getConversation(c.id);
    setActive(full);
  }

  async function send() {
    if (!active || !draft.trim()) return;
    const text = draft.trim();
    setDraft("");
    setBusy(true);
    const userMsg: ChatMsg = { role: "user", text, ts: new Date().toISOString() };
    setActive({ ...active, messages: [...active.messages, userMsg] });
    try {
      const reply = await api.sendMessage(active.id, text);
      setActive((a) => (a ? { ...a, messages: [...a.messages, reply] } : a));
    } finally { setBusy(false); }
  }

  async function injectHint() {
    if (!active?.task_id) return;
    await api.injectHint(active.task_id, hintPhase, "hint injecté depuis le chat").catch(() => {});
    const note: ChatMsg = {
      role: "assistant",
      text: `Hint injecté : phase « ${hintPhase} » priorisée. Le Planner le consommera en premier au prochain cycle.`,
      ts: new Date().toISOString(),
    };
    setActive((a) => (a ? { ...a, messages: [...a.messages, note] } : a));
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-110px)] max-w-7xl gap-4">
      {/* Liste des conversations */}
      <div className="flex w-72 shrink-0 flex-col">
        <div className="mb-3 space-y-2">
          <button className="btn-primary w-full" onClick={() => newConversation()}>
            + Nouvelle conversation
          </button>
          <select className="input" defaultValue=""
                  onChange={(e) => { if (e.target.value) newConversation(e.target.value); e.target.value = ""; }}>
            <option value="">+ liée à une tâche…</option>
            {tasks.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
        <div className="card flex-1 overflow-y-auto p-2">
          {convs.length === 0 && <p className="p-4 text-sm text-nzoyi-slate">Aucune conversation.</p>}
          {convs.map((c) => (
            <button key={c.id} onClick={() => open(c)}
              className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                active?.id === c.id ? "bg-nzoyi-orange/10 text-nzoyi-orange" : "hover:bg-nzoyi-bg"
              }`}>
              <p className="truncate font-medium">{c.title}</p>
              <p className="text-xs text-nzoyi-slate">
                {c.task_id ? "main agent · tâche" : "générale"} · {c.created_at.slice(5, 16).replace("T", " ")}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Thread */}
      <div className="card flex flex-1 flex-col">
        {!active ? (
          <div className="flex flex-1 items-center justify-center text-sm text-nzoyi-slate">
            Sélectionnez ou créez une conversation avec le main agent.
          </div>
        ) : (
          <>
            <div className="mb-3 flex items-center justify-between border-b border-nzoyi-border pb-3">
              <div>
                <p className="flex items-center gap-2 font-semibold">
                  <img src="/openzoyi-bee.png" alt="" className="h-5 w-5" /> Main agent
                </p>
                <p className="text-xs text-nzoyi-slate">
                  Human-in-the-loop · injecte des hints / intents prioritaires
                </p>
              </div>
              {active.task_id && (
                <div className="flex items-center gap-2">
                  <select className="input h-9 w-28 py-1 text-xs" value={hintPhase}
                          onChange={(e) => setHintPhase(e.target.value)}>
                    {PHASES.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                  <button className="btn-ghost h-9 py-1 text-xs" onClick={injectHint}>
                    Injecter un hint
                  </button>
                </div>
              )}
            </div>

            <div ref={threadRef} className="flex-1 space-y-3 overflow-y-auto pr-1">
              {active.messages.length === 0 && (
                <p className="py-8 text-center text-sm text-nzoyi-slate">
                  Demandez un résumé de situation, une orientation, ou injectez un hint.
                </p>
              )}
              {active.messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[78%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
                    m.role === "user" ? "bg-nzoyi-ink text-white" : "bg-nzoyi-bg text-nzoyi-ink"
                  }`}>
                    {m.text}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 flex items-center gap-2 border-t border-nzoyi-border pt-3">
              <input className="input flex-1" placeholder="Message au main agent…"
                     value={draft} onChange={(e) => setDraft(e.target.value)}
                     onKeyDown={(e) => { if (e.key === "Enter") send(); }} disabled={busy} />
              <button className="btn-primary" onClick={send} disabled={busy || !draft.trim()}>
                {busy ? "…" : "Envoyer"}
              </button>
            </div>
            <p className="mt-2 text-[11px] text-nzoyi-slate">
              Couche stratégique — analyse déterministe du graphe (repli), LLM optionnel.
              Jamais dans la boucle d'évasion RL.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
