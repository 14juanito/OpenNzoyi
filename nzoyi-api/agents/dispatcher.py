"""Dispatcher — resolves an intent into a concrete, guarded tool execution.

Pipeline per intent (mission brief, section 9), Phase 2 subset:

    scope check → rl.next_action(state, phase) → tool.run(evasion params)
    → EvaluationAgent.reward → rl.update → graph.write_back

Full gates (interception, budget, untrusted boundary) and the noise governor are
added in Phase 4; a minimal in-scope check is enforced here already so the RL can
*propose* an out-of-scope target but the dispatcher still refuses to run it.
"""

from __future__ import annotations

import ipaddress
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agents.evaluation import compute_reward
from agents.planner import Intent
from graph.assets import AssetGraph
from graph.exploration import ExplorationGraph
from tools.registry import ToolRegistry

_CORE_DIR = Path(__file__).resolve().parent.parent.parent / "nzoyi-core"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))
from evasion.action import action_hash, enumerate_action_hashes  # noqa: E402


@dataclass
class DispatchOutcome:
    intent: Intent
    tool: str
    ran: bool
    reason: str = ""
    reward: float = 0.0
    facts: int = 0
    findings: int = 0


def host_of(target: str) -> str:
    if "://" in target:
        return urlparse(target).hostname or target
    return target.split(":")[0]


def in_scope(host: str, scope: dict[str, Any], assets: AssetGraph) -> bool:
    # Scope authority is the declared CIDR / domain set. Membership in `assets`
    # is an additional anti-invention check enforced by the full scope gate
    # (Phase 4); it never *widens* scope on its own.
    # In a declared CIDR?
    for cidr in scope.get("cidrs", []):
        try:
            if ipaddress.ip_address(host) in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            pass
    # In a declared domain?
    for dom in scope.get("domains", []):
        if host == dom or host.endswith("." + dom):
            return True
    return False


class Dispatcher:
    def __init__(
        self,
        task_id: str,
        scope: dict[str, Any],
        graph: ExplorationGraph,
        assets: AssetGraph,
        registry: ToolRegistry,
        rl_client: Any,
    ) -> None:
        self.task_id = task_id
        self.scope = scope
        self.graph = graph
        self.assets = assets
        self.registry = registry
        self.rl = rl_client

    def _state(self, target: str, phase: str) -> dict[str, str]:
        host = host_of(target)
        os_guess = "linux"
        n_ports = 0
        for fact in self.graph.nodes_of("fact"):
            if fact.content.get("kind") != "recon":
                continue
            services = fact.content.get("services", [])
            n_ports = max(n_ports, len(services))
            for svc in services:
                if svc.get("port") in (445, 139, 3389) or "windows" in str(
                    svc.get("product", "")
                ).lower():
                    os_guess = "windows"
        ports_bucket = "0-3" if n_ports <= 3 else ("4-10" if n_ports <= 10 else "11+")
        return {
            "target_os": os_guess,
            "open_ports_bucket": ports_bucket,
            "privilege_level": "user",
            "alert_count_5min": "0",
            "sdn_flow_blocks": "0",
            "phase": phase,
        }

    async def dispatch(self, intent: Intent) -> DispatchOutcome:
        host = host_of(intent.target)
        if not in_scope(host, self.scope, self.assets):
            self.graph.set_status(intent.intent_node_id, "denied")
            return DispatchOutcome(
                intent, tool="", ran=False, reason=f"hors scope: {host}"
            )

        state = self._state(intent.target, intent.phase)
        decision = self.rl.next_action(self.task_id, state, intent.phase)
        rl_tool = decision["tool"]

        # Honor the RL's tool when registered for this phase; else fall back to
        # the first registered tool of the phase and recompute the action hash
        # so the reward maps to what actually ran.
        tool = self.registry.get(rl_tool)
        if tool is None or intent.phase not in tool.phases:
            phase_tools = self.registry.for_phase(intent.phase)
            if not phase_tools:
                self.graph.set_status(intent.intent_node_id, "failed")
                return DispatchOutcome(
                    intent, tool=rl_tool, ran=False,
                    reason=f"aucun outil enregistré pour la phase {intent.phase}",
                )
            tool = phase_tools[0]
            ah = action_hash(tool.name, decision["timing"], decision["delay"],
                             decision["frag"])
            if ah not in enumerate_action_hashes(intent.phase):
                ah = decision["action_hash"]
        else:
            ah = decision["action_hash"]

        self.graph.set_status(intent.intent_node_id, "running")
        result = await tool.run(
            intent.target,
            timing=decision["timing"],
            frag=decision["frag"],
            **intent.params,
        )

        facts, findings, gain = self._write_back(intent, tool.name, result)

        reward = compute_reward(result, objective_gain=gain)
        next_state = dict(state)  # Phase 2: no explicit phase transition yet
        self.rl.update(self.task_id, state, ah, reward.value, next_state)

        self.graph.set_status(
            intent.intent_node_id, "done" if result.success else "failed"
        )
        return DispatchOutcome(
            intent=intent, tool=tool.name, ran=not result.skipped,
            reason="skipped (binaire absent)" if result.skipped else "",
            reward=reward.value, facts=facts, findings=findings,
        )

    def _write_back(self, intent: Intent, tool_name: str, result) -> tuple[int, int, float]:
        facts = findings = 0
        gain = 0.0
        parsed = result.parsed or {}

        if intent.phase == "recon":
            services = parsed.get("hosts", [{}])
            svc_list = services[0].get("ports", []) if services else []
            for p in svc_list:
                self.assets.add("service", f"{host_of(intent.target)}:{p['port']}",
                                metadata=p)
            fact = self.graph.add_node(
                "fact",
                {"kind": "recon", "target": host_of(intent.target),
                 "services": svc_list},
                agent="dispatcher",
            )
            self.graph.add_edge(intent.intent_node_id, fact.id, "yields")
            facts = 1
            gain = min(len(svc_list), 5) * 1.0

        elif intent.phase == "vuln":
            fact = self.graph.add_node(
                "fact", {"kind": "vuln", "target": intent.target}, agent="dispatcher"
            )
            self.graph.add_edge(intent.intent_node_id, fact.id, "yields")
            facts = 1
            for f in parsed.get("findings", []):
                node = self.graph.add_node(
                    "finding",
                    {"title": f.get("name") or f.get("template_id"),
                     "severity": f.get("severity", "info"),
                     "matched_at": f.get("matched_at"), "tool": tool_name},
                    agent="dispatcher",
                )
                self.graph.add_edge(fact.id, node.id, "proves")
                findings += 1
            gain = min(findings, 5) * 1.0 + 0.5

        elif intent.phase == "ad_enum":
            fact = self.graph.add_node(
                "fact",
                {"kind": "ad_enum", "target": host_of(intent.target),
                 "hosts": parsed.get("hosts", []), "shares": parsed.get("shares", [])},
                agent="dispatcher",
            )
            self.graph.add_edge(intent.intent_node_id, fact.id, "yields")
            facts = 1
            gain = (min(len(parsed.get("shares", [])), 5) + 0.5)

        return facts, findings, gain
