"""HTTP API tests (TestClient) + deterministic task-manager run."""

import asyncio

from fastapi.testclient import TestClient

import server
from server import app, MANAGER, TaskCreate

client = TestClient(app)


def test_health_and_task_crud():
    assert client.get("/health").json()["status"] == "ok"
    r = client.post("/api/tasks", json={
        "name": "t", "target": "192.168.100.11",
        "scope": {"cidrs": ["192.168.100.0/24"], "domains": []},
        "profile": "quiet",
    })
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    assert client.get(f"/api/tasks/{tid}").json()["target"] == "192.168.100.11"
    assert any(t["id"] == tid for t in client.get("/api/tasks").json())
    assert client.get("/api/tasks/does-not-exist").status_code == 404


def test_invalid_profile_rejected():
    r = client.post("/api/tasks", json={"target": "x", "profile": "ludicrous"})
    assert r.status_code == 422


def test_manager_runs_engine_and_emits_events():
    task = MANAGER.create(TaskCreate(
        name="run", target="192.168.100.11",
        scope={"cidrs": ["192.168.100.0/24"], "domains": []}, profile="quiet",
    ))
    asyncio.run(MANAGER.run(task["id"]))
    assert MANAGER.tasks[task["id"]]["status"] == "done"
    types = {e["type"] for e in MANAGER.events[task["id"]]}
    assert "task_started" in types and "task_done" in types
    # findings endpoint reads from the stored result
    findings = client.get(f"/api/tasks/{task['id']}/findings").json()
    assert isinstance(findings, list)
    graph = client.get(f"/api/tasks/{task['id']}/graph").json()
    assert "nodes" in graph and "edges" in graph


def test_delete_task_marks_killed():
    task = MANAGER.create(TaskCreate(target="192.168.100.11"))
    r = client.delete(f"/api/tasks/{task['id']}")
    assert r.json()["status"] == "killed"
