"""NZOYI HTTP API (nzoyi-api) — backend for the web UI.

In-memory task manager driving the engine; findings, graph, assets, a live SSE
event stream, plus approvals and LLM-profile stubs. A PostgreSQL-backed
repository replaces the in-memory store in a later iteration; the HTTP contract
(mission brief, section 6) is stable.
"""

from __future__ import annotations

import asyncio
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from engine import Engine, EngineResult
from evidence.capture import GLOBAL_STORE
from gates.approvals import GLOBAL_APPROVALS
from knowledge.attack import coverage as attack_coverage
from knowledge.tool_signatures import prior_detection
from agents.killchain import reconstruct as reconstruct_killchain
from gates.rules_store import GLOBAL_RULES
from security.secrets import GLOBAL_SECRETS, SecretError
from store.repository import get_repository

_SEV = ["critical", "high", "medium", "low", "info"]

app = FastAPI(title="NZOYI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ── task manager ─────────────────────────────────────────────────────────
class TaskManager:
    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self.events: dict[str, list[dict]] = {}
        self.subscribers: dict[str, list[asyncio.Queue]] = {}
        self.results: dict[str, EngineResult] = {}
        self.repo = get_repository()
        # Restore persisted tasks so they survive a restart (Niveau 4).
        for t in self.repo.list_tasks():
            self.tasks[t["id"]] = t
            self.events.setdefault(t["id"], [])
            self.subscribers.setdefault(t["id"], [])

    def create(self, payload: "TaskCreate") -> dict[str, Any]:
        tid = str(uuid.uuid4())
        task = {
            "id": tid,
            "name": payload.name,
            "target": payload.target,
            "scope": payload.scope or {"cidrs": [], "domains": []},
            "profile": payload.profile,
            "status": "pending",
            "budget_tokens": payload.budget_tokens,
            "budget_turns": payload.budget_turns,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.tasks[tid] = task
        self.events[tid] = []
        self.subscribers[tid] = []
        self.repo.save_task(task)
        return task

    def _emit(self, tid: str, event: dict) -> None:
        event = {**event, "ts": datetime.now(timezone.utc).isoformat()}
        self.events[tid].append(event)
        for q in list(self.subscribers.get(tid, [])):
            q.put_nowait(event)

    async def run(self, tid: str) -> None:
        task = self.tasks[tid]
        task["status"] = "running"
        self.repo.set_task_status(tid, "running")
        self._emit(tid, {"type": "status", "status": "running"})
        engine = Engine()
        try:
            result = await engine.run(
                target=task["target"], scope=task["scope"], name=task["name"],
                profile=task["profile"], task_id=tid,
                on_event=lambda e: self._emit(tid, e),
            )
            self.results[tid] = result
            task["status"] = "done"
            report = result.report()
            self.repo.set_task_status(tid, "done")
            self.repo.save_findings(tid, report["findings"])
            self._emit(tid, {"type": "status", "status": "done",
                             "summary": report["summary"]})
        except Exception as exc:  # noqa: BLE001
            task["status"] = "failed"
            self.repo.set_task_status(tid, "failed")
            self._emit(tid, {"type": "status", "status": "failed", "error": str(exc)})
        finally:
            for q in list(self.subscribers.get(tid, [])):
                q.put_nowait({"type": "eof"})


MANAGER = TaskManager()


# ── schemas ──────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    name: str = "audit"
    target: str
    scope: dict[str, Any] | None = None
    profile: str = Field("balanced", pattern="^(quiet|balanced|aggressive)$")
    llm_profile_id: str | None = None
    budget_tokens: int | None = None
    budget_turns: int | None = None


# ── endpoints ────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "nzoyi-api", "tasks": len(MANAGER.tasks)}


def _task_findings(tid: str) -> list[dict[str, Any]]:
    result = MANAGER.results.get(tid)
    if result:
        return result.report()["findings"]
    # No live run in memory → read persisted findings (survives restart).
    return MANAGER.repo.list_task_findings(tid)


def _sev_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {s: 0 for s in _SEV}
    for f in findings:
        counts[f.get("severity", "info")] = counts.get(f.get("severity", "info"), 0) + 1
    return counts


def _task_summary(task: dict[str, Any]) -> dict[str, Any]:
    tid = task["id"]
    findings = _task_findings(tid)
    result = MANAGER.results.get(tid)
    steps = len(result.outcomes) if result else 0
    ran = sum(1 for o in result.outcomes if o.ran) if result else 0
    return {
        **task,
        "findings_count": len(findings),
        "findings_by_severity": _sev_counts(findings),
        "steps": steps,
        "steps_ran": ran,
    }


@app.get("/api/tasks")
def list_tasks() -> list[dict[str, Any]]:
    return [_task_summary(t) for t in MANAGER.tasks.values()]


@app.get("/api/findings")
def all_findings(dedup: bool = False) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for tid in MANAGER.tasks:
        tname = MANAGER.tasks.get(tid, {}).get("name", tid)
        for f in _task_findings(tid):
            items.append({**f, "task_id": tid, "task_name": tname})
    order = {s: i for i, s in enumerate(_SEV)}
    items.sort(key=lambda f: order.get(f["severity"], 99))
    counts = _sev_counts(items)
    pending = sum(1 for f in items if f.get("status") in (None, "unverified", "pending"))

    out_items = items
    if dedup:
        groups: dict[tuple, dict[str, Any]] = {}
        for f in items:
            key = (f.get("title"), f.get("severity"))
            g = groups.get(key)
            if g is None:
                groups[key] = {**f, "instances": 1, "assets": [f.get("matched_at")]}
            else:
                g["instances"] += 1
                if f.get("matched_at") not in g["assets"]:
                    g["assets"].append(f.get("matched_at"))
        out_items = sorted(groups.values(),
                           key=lambda f: order.get(f["severity"], 99))

    return {
        "total": len(items),
        "unique": len(out_items) if dedup else len(items),
        "pending": pending,
        "by_severity": counts,
        "findings": out_items,
    }


# ── secret manager (AES-256-GCM) ─────────────────────────────────────────
class SecretIn(BaseModel):
    name: str
    value: str


@app.get("/api/secrets")
def list_secrets() -> list[dict[str, str]]:
    return GLOBAL_SECRETS.list()


@app.post("/api/secrets")
def set_secret(s: SecretIn) -> dict[str, str]:
    try:
        return GLOBAL_SECRETS.set(s.name, s.value)
    except SecretError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.delete("/api/secrets/{name}")
def delete_secret(name: str) -> dict[str, Any]:
    return {"name": name, "deleted": GLOBAL_SECRETS.delete(name)}


# ── interception rules editor ────────────────────────────────────────────
class RuleIn(BaseModel):
    rule_type: str
    pattern: Any
    action: str


@app.get("/api/interception-rules")
def list_rules() -> list[dict[str, Any]]:
    return GLOBAL_RULES.list()


@app.post("/api/interception-rules")
def add_rule(r: RuleIn) -> dict[str, Any]:
    try:
        return GLOBAL_RULES.add(r.rule_type, r.pattern, r.action)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.delete("/api/interception-rules/{rid}")
def delete_rule(rid: int) -> dict[str, Any]:
    return {"id": rid, "deleted": GLOBAL_RULES.delete(rid)}


def _tool_calls(tid: str) -> list[dict[str, Any]]:
    return [e for e in MANAGER.events.get(tid, []) if e.get("type") == "tool_call"]


@app.get("/api/attack-coverage")
def attack_cov(task_id: str | None = None) -> dict[str, Any]:
    """MITRE ATT&CK coverage matrix (tactics x techniques)."""
    findings: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    tids = [task_id] if task_id else list(MANAGER.results.keys())
    for tid in tids:
        result = MANAGER.results.get(tid)
        if result:
            findings += result.report()["findings"]
        tool_calls += _tool_calls(tid)
    return attack_coverage(findings, tool_calls)


@app.get("/api/tasks/{tid}/killchain")
def killchain(tid: str) -> dict[str, Any]:
    result = MANAGER.results.get(tid)
    if result is None:
        return {"steps": [], "summary": "Tâche sans graphe.", "length": 0}
    return reconstruct_killchain(result.graph.to_dict())


def _telemetry_for(tid: str) -> dict[str, Any]:
    calls = _tool_calls(tid)
    reward_series = [
        {"step": i + 1, "phase": c.get("phase"), "tool": c.get("tool"),
         "reward": c.get("reward", 0), "ran": c.get("ran", False)}
        for i, c in enumerate(calls)
    ]
    # Predicted (prior) vs observed (IDS alerts) detection, per distinct tool.
    tools = sorted({c.get("tool") for c in calls if c.get("tool")})
    detection = [
        {"tool": t, "predicted": round(prior_detection(t), 2), "observed_alerts": 0}
        for t in tools
    ]
    total_alerts = 0  # live IDS telemetry wires in with the lab (Phase 4+)
    # Stealth score in [0,1]: 1 when no alert was generated.
    steps = max(1, len(calls))
    stealth = round(max(0.0, 1.0 - total_alerts / (steps * 3.0)), 3)
    return {
        "task_id": tid,
        "reward_series": reward_series,
        "detection": detection,
        "total_alerts": total_alerts,
        "stealth_score": stealth,
        "epsilon": float(os.environ.get("NZOYI_RL_EPSILON", "0.2")),
        "steps": len(calls),
    }


@app.get("/api/tasks/{tid}/telemetry")
def task_telemetry(tid: str) -> dict[str, Any]:
    if tid not in MANAGER.tasks:
        raise HTTPException(404, "tâche inconnue")
    return _telemetry_for(tid)


@app.get("/api/telemetry")
def global_telemetry() -> dict[str, Any]:
    per_task = [_telemetry_for(tid) for tid in MANAGER.tasks]
    scores = [t["stealth_score"] for t in per_task if t["steps"] > 0]
    avg_stealth = round(sum(scores) / len(scores), 3) if scores else None
    return {
        "tasks": len(per_task),
        "avg_stealth_score": avg_stealth,
        "total_steps": sum(t["steps"] for t in per_task),
        "total_alerts": sum(t["total_alerts"] for t in per_task),
        "per_task": per_task,
    }


@app.get("/api/traffic")
def traffic(task_id: str | None = None, limit: int = 200) -> dict[str, Any]:
    flows = [
        ev.to_dict() for ev in GLOBAL_STORE.all()
        if task_id is None or ev.task_id == task_id
    ]
    flows.sort(key=lambda e: e["captured_at"], reverse=True)
    return {"count": len(flows), "flows": flows[:limit], "proxy_port": 8788}


@app.get("/api/tasks/{tid}/sessions")
def task_sessions(tid: str) -> dict[str, Any]:
    if tid not in MANAGER.tasks:
        raise HTTPException(404, "tâche inconnue")
    events = MANAGER.events.get(tid, [])
    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    workers = [
        {
            "phase": e.get("phase"), "tool": e.get("tool"), "target": e.get("target"),
            "ran": e.get("ran"), "reward": e.get("reward"), "findings": e.get("findings"),
            "ts": e.get("ts"),
        }
        for e in tool_calls
    ]
    return {"events": events, "workers": workers}


@app.post("/api/tasks")
async def create_task(payload: TaskCreate) -> dict[str, Any]:
    task = MANAGER.create(payload)
    asyncio.create_task(MANAGER.run(task["id"]))
    return task


@app.get("/api/tasks/{tid}")
def get_task(tid: str) -> dict[str, Any]:
    if tid not in MANAGER.tasks:
        raise HTTPException(404, "tâche inconnue")
    return MANAGER.tasks[tid]


@app.delete("/api/tasks/{tid}")
def delete_task(tid: str) -> dict[str, Any]:
    if tid not in MANAGER.tasks:
        raise HTTPException(404, "tâche inconnue")
    MANAGER.tasks[tid]["status"] = "killed"
    MANAGER._emit(tid, {"type": "status", "status": "killed"})
    return {"id": tid, "status": "killed"}


@app.get("/api/tasks/{tid}/stream")
async def stream(tid: str) -> StreamingResponse:
    if tid not in MANAGER.tasks:
        raise HTTPException(404, "tâche inconnue")
    queue: asyncio.Queue = asyncio.Queue()
    # Replay history, then live.
    for ev in MANAGER.events[tid]:
        queue.put_nowait(ev)
    MANAGER.subscribers[tid].append(queue)

    async def gen():
        try:
            while True:
                ev = await queue.get()
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                if ev.get("type") == "eof":
                    break
        finally:
            if queue in MANAGER.subscribers.get(tid, []):
                MANAGER.subscribers[tid].remove(queue)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/tasks/{tid}/findings")
def task_findings(tid: str) -> list[dict[str, Any]]:
    result = MANAGER.results.get(tid)
    if result is None:
        return []
    return result.report()["findings"]


@app.get("/api/tasks/{tid}/graph")
def task_graph(tid: str) -> dict[str, Any]:
    result = MANAGER.results.get(tid)
    if result is None:
        return {"nodes": [], "edges": []}
    return result.graph.to_dict()


@app.get("/api/assets")
def assets(task_id: str) -> list[dict[str, Any]]:
    result = MANAGER.results.get(task_id)
    if result is None:
        return []
    return [{"id": a.id, "type": a.type, "value": a.value} for a in result.assets.all()]


@app.get("/api/findings/{fid}")
def get_finding(fid: str) -> dict[str, Any]:
    for result in MANAGER.results.values():
        for f in result.report()["findings"]:
            if f["id"] == fid:
                return f
    raise HTTPException(404, "finding inconnu")


@app.post("/api/findings/{fid}/retest")
def retest_finding(fid: str) -> dict[str, Any]:
    return {"id": fid, "retest_status": "queued"}


# ── approval records (interception audit trail) ──────────────────────────
@app.get("/api/approvals")
def approvals() -> list[dict[str, Any]]:
    """Pending approvals (awaiting a human decision)."""
    return [r.to_dict() for r in GLOBAL_APPROVALS.pending()]


@app.get("/api/approval-records")
def approval_records() -> dict[str, Any]:
    """Full audit trail of interception decisions."""
    records = [r.to_dict() for r in GLOBAL_APPROVALS.all()]
    pending = [r for r in records if r["status"] == "pending"]
    return {"total": len(records), "pending_count": len(pending), "records": records}


class Decision(BaseModel):
    status: str = Field(pattern="^(allowed|denied)$")


@app.post("/api/approvals/{seq}/decide")
def decide(seq: int, decision: Decision) -> dict[str, Any]:
    rec = GLOBAL_APPROVALS.decide(seq, decision.status, decided_by="human")
    if rec is None:
        raise HTTPException(404, "approbation inconnue")
    return rec.to_dict()


# ── chat with the main agent (human-in-the-loop) ─────────────────────────
from agents.main_agent import analyze as _analyze  # noqa: E402

_CONVERSATIONS: dict[str, dict[str, Any]] = {}


class ConvCreate(BaseModel):
    title: str = "Nouvelle conversation"
    task_id: str | None = None


class ChatMessage(BaseModel):
    text: str


class Hint(BaseModel):
    phase: str
    target: str | None = None
    text: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/api/chat/conversations")
def list_conversations() -> list[dict[str, Any]]:
    return sorted(_CONVERSATIONS.values(), key=lambda c: c["created_at"], reverse=True)


@app.post("/api/chat/conversations")
def create_conversation(body: ConvCreate) -> dict[str, Any]:
    cid = str(uuid.uuid4())
    conv = {"id": cid, "title": body.title, "task_id": body.task_id,
            "created_at": _now_iso(), "messages": []}
    _CONVERSATIONS[cid] = conv
    return conv


@app.get("/api/chat/conversations/{cid}")
def get_conversation(cid: str) -> dict[str, Any]:
    if cid not in _CONVERSATIONS:
        raise HTTPException(404, "conversation inconnue")
    return _CONVERSATIONS[cid]


@app.post("/api/chat/conversations/{cid}/message")
def post_message(cid: str, msg: ChatMessage) -> dict[str, Any]:
    conv = _CONVERSATIONS.get(cid)
    if conv is None:
        raise HTTPException(404, "conversation inconnue")
    conv["messages"].append({"role": "user", "text": msg.text, "ts": _now_iso()})

    tid = conv.get("task_id")
    task = MANAGER.tasks.get(tid) if tid else None
    graph = MANAGER.results[tid].graph.to_dict() if (tid and tid in MANAGER.results) else {"nodes": []}
    reply = _analyze(task or {"target": "—"}, graph, msg.text)
    assistant = {"role": "assistant", "text": reply, "ts": _now_iso()}
    conv["messages"].append(assistant)
    return assistant


@app.post("/api/tasks/{tid}/hint")
def inject_hint(tid: str, hint: Hint) -> dict[str, Any]:
    if tid not in MANAGER.tasks:
        raise HTTPException(404, "tâche inconnue")
    result = MANAGER.results.get(tid)
    if result is None:
        raise HTTPException(409, "la tâche n'a pas encore de graphe d'exploration")
    target = hint.target or MANAGER.tasks[tid]["target"]
    node = result.graph.add_node(
        "hint", {"phase": hint.phase, "target": target, "text": hint.text},
        status="open", agent="operator",
    )
    MANAGER._emit(tid, {"type": "hint", "phase": hint.phase, "target": target})
    return {"id": node.id, "phase": hint.phase, "target": target, "status": "open"}


# ── LLM profiles (stub) ──────────────────────────────────────────────────
_LLM_PROFILES: list[dict[str, Any]] = []


@app.get("/api/llm/profiles")
def llm_profiles() -> list[dict[str, Any]]:
    return _LLM_PROFILES


@app.post("/api/llm/profiles")
def create_llm_profile(profile: dict[str, Any]) -> dict[str, Any]:
    profile = {"id": str(uuid.uuid4()), **profile}
    _LLM_PROFILES.append(profile)
    return profile
