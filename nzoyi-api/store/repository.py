"""Niveau 4 — persistance PostgreSQL des tâches et findings.

Fait survivre les tâches et leurs findings à un redémarrage (le graphe/la
télémétrie restent des artefacts de run en mémoire). Repli mémoire déterministe
quand ``NZOYI_DATABASE_URL`` / ``DATABASE_URL`` est absent — le comportement
actuel (et les tests) est préservé sans base.

Écrit sur le schéma Alembic de la Phase 1 (tables ``tasks`` et ``findings``).
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any


class Repository(ABC):
    @abstractmethod
    def save_task(self, task: dict[str, Any]) -> None: ...
    @abstractmethod
    def set_task_status(self, task_id: str, status: str) -> None: ...
    @abstractmethod
    def list_tasks(self) -> list[dict[str, Any]]: ...
    @abstractmethod
    def save_findings(self, task_id: str, findings: list[dict[str, Any]]) -> None: ...
    @abstractmethod
    def list_task_findings(self, task_id: str) -> list[dict[str, Any]]: ...


class MemoryRepository(Repository):
    """No-op persistence: the TaskManager's own in-memory maps are the truth."""

    def save_task(self, task: dict[str, Any]) -> None: ...
    def set_task_status(self, task_id: str, status: str) -> None: ...
    def list_tasks(self) -> list[dict[str, Any]]:
        return []
    def save_findings(self, task_id: str, findings: list[dict[str, Any]]) -> None: ...
    def list_task_findings(self, task_id: str) -> list[dict[str, Any]]:
        return []


_SEV = {"info", "low", "medium", "high", "critical"}


class PostgresRepository(Repository):
    def __init__(self, database_url: str) -> None:
        from sqlalchemy import create_engine

        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+psycopg2://", 1)
        self._engine = create_engine(database_url, pool_pre_ping=True, future=True)

    def save_task(self, task: dict[str, Any]) -> None:
        from sqlalchemy import text

        sql = text(
            "INSERT INTO tasks (id, name, target, scope, profile, status, "
            "budget_tokens, budget_turns) VALUES (:id, :name, :target, "
            "CAST(:scope AS JSONB), :profile, :status, :bt, :bu) "
            "ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, "
            "updated_at = now()"
        )
        with self._engine.begin() as c:
            c.execute(sql, {
                "id": task["id"], "name": task["name"], "target": task["target"],
                "scope": json.dumps(task.get("scope", {})),
                "profile": task.get("profile", "balanced"),
                "status": task.get("status", "pending"),
                "bt": task.get("budget_tokens"), "bu": task.get("budget_turns"),
            })

    def set_task_status(self, task_id: str, status: str) -> None:
        from sqlalchemy import text

        with self._engine.begin() as c:
            c.execute(text("UPDATE tasks SET status=:s, updated_at=now() WHERE id=:id"),
                      {"s": status, "id": task_id})

    def list_tasks(self) -> list[dict[str, Any]]:
        from sqlalchemy import text

        sql = text(
            "SELECT id, name, target, scope, profile, status, budget_tokens, "
            "budget_turns, created_at FROM tasks ORDER BY created_at DESC")
        with self._engine.connect() as c:
            rows = c.execute(sql).mappings().all()
        return [{
            "id": str(r["id"]), "name": r["name"], "target": r["target"],
            "scope": r["scope"], "profile": r["profile"], "status": r["status"],
            "budget_tokens": r["budget_tokens"], "budget_turns": r["budget_turns"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        } for r in rows]

    def save_findings(self, task_id: str, findings: list[dict[str, Any]]) -> None:
        if not findings:
            return
        from sqlalchemy import text

        # Idempotent per run: clear then insert this task's findings.
        with self._engine.begin() as c:
            c.execute(text("DELETE FROM findings WHERE task_id=:t"), {"t": task_id})
            ins = text(
                "INSERT INTO findings (task_id, title, severity, status) "
                "VALUES (:t, :title, :sev, :status)")
            c.execute(ins, [{
                "t": task_id, "title": (f.get("title") or "finding")[:500],
                "sev": f["severity"] if f.get("severity") in _SEV else "info",
                "status": "unverified",
            } for f in findings])

    def list_task_findings(self, task_id: str) -> list[dict[str, Any]]:
        from sqlalchemy import text

        sql = text(
            "SELECT id, title, severity, status FROM findings WHERE task_id=:t "
            "ORDER BY created_at")
        with self._engine.connect() as c:
            rows = c.execute(sql, {"t": task_id}).mappings().all()
        return [{"id": str(r["id"]), "title": r["title"], "severity": r["severity"],
                 "matched_at": None, "tool": None, "attack": [],
                 "status": r["status"]} for r in rows]


def get_repository() -> Repository:
    url = os.environ.get("NZOYI_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if url:
        try:
            return PostgresRepository(url)
        except Exception:  # noqa: BLE001 — jamais bloquer le démarrage
            return MemoryRepository()
    return MemoryRepository()
