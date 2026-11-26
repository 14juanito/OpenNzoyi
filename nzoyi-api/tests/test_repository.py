"""Niveau 4 — persistance : MemoryRepository (toujours) + Postgres (si DB)."""

import os

import pytest

from store.repository import MemoryRepository, get_repository


def test_memory_repository_is_noop():
    r = MemoryRepository()
    r.save_task({"id": "x", "name": "n", "target": "t"})
    r.save_findings("x", [{"title": "f", "severity": "high"}])
    assert r.list_tasks() == []
    assert r.list_task_findings("x") == []


def test_get_repository_defaults_to_memory(monkeypatch):
    monkeypatch.delenv("NZOYI_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert isinstance(get_repository(), MemoryRepository)


@pytest.mark.skipif(
    not (os.environ.get("NZOYI_DATABASE_URL") or os.environ.get("DATABASE_URL")),
    reason="pas de PostgreSQL configuré",
)
def test_postgres_roundtrip():
    from store.repository import PostgresRepository

    url = os.environ.get("NZOYI_DATABASE_URL") or os.environ["DATABASE_URL"]
    repo = PostgresRepository(url)
    import uuid
    tid = str(uuid.uuid4())
    repo.save_task({"id": tid, "name": "pytest-persist", "target": "192.168.100.11",
                    "scope": {"cidrs": ["192.168.100.0/24"], "domains": []},
                    "profile": "quiet", "status": "pending"})
    repo.set_task_status(tid, "done")
    repo.save_findings(tid, [{"title": "SQLi", "severity": "high"}])
    assert any(t["id"] == tid for t in repo.list_tasks())
    fs = repo.list_task_findings(tid)
    assert fs and fs[0]["severity"] == "high"
