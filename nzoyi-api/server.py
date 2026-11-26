"""NZOYI HTTP API (nzoyi-api) — backend for the web UI.

In-memory task manager driving the engine; findings, graph, assets, a live SSE
event stream, plus approvals and LLM-profile stubs. A PostgreSQL-backed
repository replaces the in-memory store in a later iteration; the HTTP contract
(mission brief, section 6) is stable.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from engine import Engine, EngineResult

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
        return task

    def _emit(self, tid: str, event: dict) -> None:
        event = {**event, "ts": datetime.now(timezone.utc).isoformat()}
        self.events[tid].append(event)
        for q in list(self.subscribers.get(tid, [])):
            q.put_nowait(event)

    async def run(self, tid: str) -> None:
        task = self.tasks[tid]
        task["status"] = "running"
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
            self._emit(tid, {"type": "status", "status": "done",
                             "summary": result.report()["summary"]})
        except Exception as exc:  # noqa: BLE001
            task["status"] = "failed"
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


@app.get("/api/tasks")
def list_tasks() -> list[dict[str, Any]]:
    return list(MANAGER.tasks.values())


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


# ── approvals & LLM profiles (stubs — étoffés en Phase 6) ────────────────
_APPROVALS: list[dict[str, Any]] = []
_LLM_PROFILES: list[dict[str, Any]] = []


@app.get("/api/approvals")
def approvals() -> list[dict[str, Any]]:
    return _APPROVALS


@app.post("/api/approvals/{aid}/decide")
def decide(aid: str, decision: dict[str, Any]) -> dict[str, Any]:
    return {"id": aid, "status": decision.get("status", "approved")}


@app.get("/api/llm/profiles")
def llm_profiles() -> list[dict[str, Any]]:
    return _LLM_PROFILES


@app.post("/api/llm/profiles")
def create_llm_profile(profile: dict[str, Any]) -> dict[str, Any]:
    profile = {"id": str(uuid.uuid4()), **profile}
    _LLM_PROFILES.append(profile)
    return profile
