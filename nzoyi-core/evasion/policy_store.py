"""Persistence for the evasion Q-tables.

The Q-table itself lives in memory inside an ephemeral
:class:`~evasion.q_learner.EvasionQLearner` for the duration of a single HTTP
request. This module loads the relevant slice before the request and writes back
the mutated cells after, keyed by ``(task_id, phase, state_hash, action_hash)``
exactly as declared in the ``q_tables`` table (section 3 of the brief).

Two backends:

* :class:`PostgresPolicyStore` — the production store (SQLAlchemy core, upsert).
* :class:`MemoryPolicyStore` — a deterministic in-process fallback used when no
  ``DATABASE_URL`` is configured, so the microservice stays runnable and
  testable without a live database (skill principle #2: no hard network
  dependency, deterministic fallback).

Composite Q-key convention (must match ``q_learner.py``)::

    q_key = f"{state_hash}:{action_hash}"

``state_hash`` and ``action_hash`` never contain ':' (see state.py / action.py),
so ``q_key.split(":", 1)`` round-trips cleanly.
"""

from __future__ import annotations

import os
import threading
from abc import ABC, abstractmethod
from typing import Iterable


def split_q_key(q_key: str) -> tuple[str, str]:
    """Split a composite Q-key into ``(state_hash, action_hash)``."""
    state_hash, _, action_hash = q_key.partition(":")
    if not action_hash:
        raise ValueError(f"q_key composite malformé: '{q_key}'")
    return state_hash, action_hash


def make_q_key(state_hash: str, action_hash: str) -> str:
    return f"{state_hash}:{action_hash}"


class PolicyStore(ABC):
    """Load/persist Q-values for a task's evasion policy."""

    @abstractmethod
    def load_phase(self, task_id: str, phase: str) -> dict[str, float]:
        """Return ``{q_key: q_value}`` for one task/phase slice."""

    @abstractmethod
    def load_task(self, task_id: str) -> dict[str, float]:
        """Return ``{q_key: q_value}`` for every phase of a task."""

    @abstractmethod
    def upsert(self, task_id: str, phase: str, cells: dict[str, float]) -> None:
        """Insert/update Q-values for ``cells = {q_key: q_value}``."""

    @abstractmethod
    def reset(self, task_id: str) -> int:
        """Delete every Q-value for a task. Returns rows removed."""

    @abstractmethod
    def summary(self, task_id: str, phase: str | None = None) -> dict:
        """Aggregate stats (count, min/max/mean q) for a task[/phase]."""


class MemoryPolicyStore(PolicyStore):
    """Thread-safe in-process store. Volatile; for dev/tests only."""

    def __init__(self) -> None:
        # {(task_id, phase): {q_key: q_value}}
        self._data: dict[tuple[str, str], dict[str, float]] = {}
        self._lock = threading.RLock()

    def load_phase(self, task_id: str, phase: str) -> dict[str, float]:
        with self._lock:
            return dict(self._data.get((task_id, phase), {}))

    def load_task(self, task_id: str) -> dict[str, float]:
        with self._lock:
            merged: dict[str, float] = {}
            for (tid, _phase), cells in self._data.items():
                if tid == task_id:
                    merged.update(cells)
            return merged

    def upsert(self, task_id: str, phase: str, cells: dict[str, float]) -> None:
        if not cells:
            return
        with self._lock:
            bucket = self._data.setdefault((task_id, phase), {})
            bucket.update(cells)

    def reset(self, task_id: str) -> int:
        with self._lock:
            keys = [k for k in self._data if k[0] == task_id]
            removed = sum(len(self._data[k]) for k in keys)
            for k in keys:
                del self._data[k]
            return removed

    def summary(self, task_id: str, phase: str | None = None) -> dict:
        with self._lock:
            values: list[float] = []
            for (tid, ph), cells in self._data.items():
                if tid != task_id:
                    continue
                if phase is not None and ph != phase:
                    continue
                values.extend(cells.values())
        return _summarize(values)


class PostgresPolicyStore(PolicyStore):
    """SQLAlchemy-backed store against the ``q_tables`` table."""

    def __init__(self, database_url: str) -> None:
        from sqlalchemy import create_engine

        # psycopg2 driver; normalize a bare postgres:// URL and pin the driver
        # (psycopg v3 is not a dependency).
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+psycopg2://", 1
            )
        self._engine = create_engine(database_url, pool_pre_ping=True, future=True)

    def load_phase(self, task_id: str, phase: str) -> dict[str, float]:
        from sqlalchemy import text

        sql = text(
            "SELECT state_hash, action_hash, q_value FROM q_tables "
            "WHERE task_id = :task_id AND phase = :phase"
        )
        with self._engine.connect() as conn:
            rows = conn.execute(sql, {"task_id": task_id, "phase": phase})
            return {make_q_key(r[0], r[1]): float(r[2]) for r in rows}

    def load_task(self, task_id: str) -> dict[str, float]:
        from sqlalchemy import text

        sql = text(
            "SELECT state_hash, action_hash, q_value FROM q_tables "
            "WHERE task_id = :task_id"
        )
        with self._engine.connect() as conn:
            rows = conn.execute(sql, {"task_id": task_id})
            return {make_q_key(r[0], r[1]): float(r[2]) for r in rows}

    def upsert(self, task_id: str, phase: str, cells: dict[str, float]) -> None:
        if not cells:
            return
        from sqlalchemy import text

        sql = text(
            "INSERT INTO q_tables "
            "(task_id, phase, state_hash, action_hash, q_value, updated_at) "
            "VALUES (:task_id, :phase, :state_hash, :action_hash, :q_value, now()) "
            "ON CONFLICT (task_id, phase, state_hash, action_hash) "
            "DO UPDATE SET q_value = EXCLUDED.q_value, updated_at = now()"
        )
        params = []
        for q_key, q_value in cells.items():
            state_hash, action_hash = split_q_key(q_key)
            params.append(
                {
                    "task_id": task_id,
                    "phase": phase,
                    "state_hash": state_hash,
                    "action_hash": action_hash,
                    "q_value": float(q_value),
                }
            )
        with self._engine.begin() as conn:
            conn.execute(sql, params)

    def reset(self, task_id: str) -> int:
        from sqlalchemy import text

        sql = text("DELETE FROM q_tables WHERE task_id = :task_id")
        with self._engine.begin() as conn:
            result = conn.execute(sql, {"task_id": task_id})
            return int(result.rowcount or 0)

    def summary(self, task_id: str, phase: str | None = None) -> dict:
        from sqlalchemy import text

        clause = "WHERE task_id = :task_id"
        params: dict[str, object] = {"task_id": task_id}
        if phase is not None:
            clause += " AND phase = :phase"
            params["phase"] = phase
        sql = text(
            "SELECT count(*), min(q_value), max(q_value), avg(q_value) "
            f"FROM q_tables {clause}"
        )
        with self._engine.connect() as conn:
            count, qmin, qmax, qmean = conn.execute(sql, params).one()
        return {
            "count": int(count or 0),
            "q_min": float(qmin) if qmin is not None else None,
            "q_max": float(qmax) if qmax is not None else None,
            "q_mean": float(qmean) if qmean is not None else None,
        }


def _summarize(values: Iterable[float]) -> dict:
    vals = list(values)
    if not vals:
        return {"count": 0, "q_min": None, "q_max": None, "q_mean": None}
    return {
        "count": len(vals),
        "q_min": min(vals),
        "q_max": max(vals),
        "q_mean": sum(vals) / len(vals),
    }


def get_policy_store() -> PolicyStore:
    """Factory: Postgres when configured, else the in-memory fallback.

    Honors ``NZOYI_DATABASE_URL`` then ``DATABASE_URL``. The fallback is logged
    once at import of the API so operators notice they are not persisting.
    """
    url = os.environ.get("NZOYI_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if url:
        return PostgresPolicyStore(url)
    return MemoryPolicyStore()
