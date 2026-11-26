"""Planner — reads the exploration graph and emits the next intents.

Phase 2 is deliberately naive (one strategic step at a time, no LLM yet): it
turns the graph state into a short, ordered intent chain. The *strategic* choice
(which phase, which target) is the Planner's; the *tactical* choice (which
concrete tool, which evasion parameters) is delegated to the RL by the
Dispatcher. There is a single graph — the Planner does not keep a second memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from graph.assets import AssetGraph
from graph.exploration import ExplorationGraph


@dataclass
class Intent:
    phase: str
    target: str
    goal_node_id: str
    intent_node_id: str = ""
    params: dict[str, Any] = field(default_factory=dict)


# Ports that justify an AD-enumeration intent.
_SMB_PORTS = {139, 445}


class Planner:
    def __init__(self, graph: ExplorationGraph, assets: AssetGraph) -> None:
        self.graph = graph
        self.assets = assets

    def _has_fact(self, kind: str, target: str | None = None) -> bool:
        for n in self.graph.nodes_of("fact"):
            if n.content.get("kind") != kind:
                continue
            if target is None or n.content.get("target") == target:
                return True
        return False

    def plan(self) -> list[Intent]:
        """Return the intents ready to dispatch now (empty when nothing to do)."""
        goals = self.graph.nodes_of("goal", status="open")
        if not goals:
            return []
        goal = goals[0]
        target = goal.content.get("target", "")
        intents: list[Intent] = []

        # 0) Human-injected hints are consumed first (high priority).
        hints = self.graph.nodes_of("hint", status="open")
        if hints:
            for hint in hints:
                phase = hint.content.get("phase")
                htarget = hint.content.get("target") or target
                if phase:
                    self.graph.set_status(hint.id, "consumed")
                    node = self.graph.add_node(
                        "intent", {"phase": phase, "target": htarget, "from_hint": True},
                        status="open", agent="planner",
                    )
                    self.graph.add_edge(hint.id, node.id, "spawns")
                    intents.append(Intent(phase=phase, target=htarget,
                                          goal_node_id=goal.id, intent_node_id=node.id))
            if intents:
                return intents

        # 1) Recon first, once per target.
        if not self._has_fact("recon", target):
            intents.append(self._spawn("recon", target, goal.id))
            return intents  # one step at a time

        # 2) For each open HTTP-ish service, a vuln intent (once).
        for fact in self.graph.nodes_of("fact"):
            if fact.content.get("kind") != "recon":
                continue
            for svc in fact.content.get("services", []):
                if svc.get("service") in ("http", "https", "http-proxy") or svc.get(
                    "port"
                ) in (80, 443, 8080, 8443):
                    url = self._svc_url(target, svc)
                    if not self._has_fact("vuln", url):
                        intents.append(self._spawn("vuln", url, goal.id))

        # 3) AD enumeration if an SMB port is open.
        if self._smb_open() and not self._has_fact("ad_enum", target):
            intents.append(self._spawn("ad_enum", target, goal.id))

        return intents

    # ── helpers ──────────────────────────────────────────────────────────
    def _spawn(self, phase: str, target: str, goal_id: str) -> Intent:
        node = self.graph.add_node(
            "intent", {"phase": phase, "target": target}, status="open", agent="planner"
        )
        self.graph.add_edge(goal_id, node.id, "spawns")
        return Intent(
            phase=phase, target=target, goal_node_id=goal_id, intent_node_id=node.id
        )

    def _smb_open(self) -> bool:
        for fact in self.graph.nodes_of("fact"):
            if fact.content.get("kind") != "recon":
                continue
            for svc in fact.content.get("services", []):
                if svc.get("port") in _SMB_PORTS:
                    return True
        return False

    @staticmethod
    def _svc_url(target: str, svc: dict[str, Any]) -> str:
        scheme = "https" if svc.get("port") in (443, 8443) else "http"
        return f"{scheme}://{target}:{svc.get('port')}"
