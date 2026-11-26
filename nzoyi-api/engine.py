"""Orchestration loop — the Planner/Dispatcher driver (replaces the old monolith).

    graph change → Planner → intent queue → Dispatcher → graph write-back → …

Bounded by ``max_rounds`` so a misbehaving planner cannot loop forever (a crude
budget; the real token/turn budget lands in Phase 4).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from agents.dispatcher import Dispatcher, DispatchOutcome, host_of
from agents.planner import Planner
from graph.assets import AssetGraph
from graph.exploration import ExplorationGraph
from report import build_report
from rl_client import RLClient
from tools.registry import ToolRegistry, default_registry


@dataclass
class EngineResult:
    task: dict[str, Any]
    graph: ExplorationGraph
    assets: AssetGraph
    outcomes: list[DispatchOutcome] = field(default_factory=list)

    def report(self) -> dict[str, Any]:
        return build_report(self.task, self.graph, self.assets)


class Engine:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        rl_client: RLClient | None = None,
    ) -> None:
        self.registry = registry or default_registry()
        self.rl = rl_client or RLClient()

    async def run(
        self,
        target: str,
        scope: dict[str, Any] | None = None,
        name: str = "audit",
        profile: str = "balanced",
        task_id: str | None = None,
        max_rounds: int = 8,
        on_event: Any = None,
    ) -> EngineResult:
        task_id = task_id or str(uuid.uuid4())
        scope = scope or {"cidrs": [], "domains": []}
        task = {"id": task_id, "name": name, "target": target,
                "scope": scope, "profile": profile}

        graph = ExplorationGraph(task_id)
        assets = AssetGraph()
        # Seed: the goal and the root asset (the declared target).
        graph.add_node("goal", {"target": host_of(target), "objective": "audit"},
                       status="open", agent="engine")
        self._seed_asset(assets, host_of(target))

        planner = Planner(graph, assets)
        dispatcher = Dispatcher(
            task_id, scope, graph, assets, self.registry, self.rl,
            profile=profile, root_target=host_of(target),
        )

        def emit(kind: str, data: dict[str, Any]) -> None:
            if on_event is not None:
                on_event({"type": kind, **data})

        emit("task_started", {"task_id": task_id, "target": host_of(target)})
        outcomes: list[DispatchOutcome] = []
        seen_intents: set[str] = set()
        for _ in range(max_rounds):
            intents = [i for i in planner.plan() if i.intent_node_id not in seen_intents]
            if not intents:
                break
            for intent in intents:
                seen_intents.add(intent.intent_node_id)
                emit("intent", {"phase": intent.phase, "target": intent.target})
                outcome = await dispatcher.dispatch(intent)
                outcomes.append(outcome)
                emit("tool_call", {
                    "phase": intent.phase, "target": intent.target,
                    "tool": outcome.tool, "ran": outcome.ran,
                    "reason": outcome.reason, "reward": round(outcome.reward, 3),
                    "findings": outcome.findings,
                })

        rep = build_report(task, graph, assets)
        emit("task_done", {"task_id": task_id, "summary": rep["summary"]})
        return EngineResult(task=task, graph=graph, assets=assets, outcomes=outcomes)

    @staticmethod
    def _seed_asset(assets: AssetGraph, host: str) -> None:
        import ipaddress

        try:
            ipaddress.ip_address(host)
            assets.add("ip", host)
        except ValueError:
            assets.add("domain", host)
