"""Dispatcher — resolves an intent into a concrete, guarded tool execution.

Pipeline per intent (mission brief, section 9):

    scope gate → interception gate → budget → rl.next_action(state, phase)
    → noise governor (clamp) → tool.run → evidence.capture/link
    → EvaluationAgent.reward → rl.update → graph.write_back

Gates and the governor are optional constructor arguments: when omitted the
dispatcher builds safe defaults (autonomous interception, balanced governor, no
budget ceiling), so the Phase 2/3 call sites keep working unchanged.
"""

from __future__ import annotations

import ipaddress
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agents.evaluation import compute_reward
from agents.noise_governor import NoiseGovernor
from agents.planner import Intent
from gates.approvals import GLOBAL_APPROVALS
from gates.budget import Budget
from gates.interception_gate import ApprovalRule, InterceptionGate
from gates.scope_gate import ScopeGate
from graph.assets import AssetGraph
from graph.exploration import ExplorationGraph
from knowledge.tool_signatures import attack_techniques
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
    effective_delay_ms: float = 0.0


def host_of(target: str) -> str:
    if "://" in target:
        return urlparse(target).hostname or target
    return target.split(":")[0]


class Dispatcher:
    def __init__(
        self,
        task_id: str,
        scope: dict[str, Any],
        graph: ExplorationGraph,
        assets: AssetGraph,
        registry: ToolRegistry,
        rl_client: Any,
        *,
        profile: str = "balanced",
        interception_mode: str = "autonomous",
        approval_rules: list[ApprovalRule] | None = None,
        budget: Budget | None = None,
        governor: NoiseGovernor | None = None,
        evidence_store: Any = None,
        root_target: str | None = None,
        task_name: str = "",
    ) -> None:
        self.task_id = task_id
        self.task_name = task_name or task_id
        self._worker_seq = 0
        self.scope = scope
        self.graph = graph
        self.assets = assets
        self.registry = registry
        self.rl = rl_client
        self.budget = budget
        self.evidence = evidence_store
        self.governor = governor or NoiseGovernor(profile)
        self.interception = InterceptionGate(approval_rules, mode=interception_mode)
        self.scope_gate = ScopeGate(
            scope, known_assets=self.assets.values, root_target=root_target
        )

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

        # ── scope gate ───────────────────────────────────────────────────
        if not self.scope_gate.check(host).allowed:
            self.graph.set_status(intent.intent_node_id, "denied")
            return DispatchOutcome(intent, tool="", ran=False,
                                   reason=f"hors scope: {host}")

        # ── budget gate ──────────────────────────────────────────────────
        if self.budget is not None and self.budget.should_wrap_up():
            self.graph.set_status(intent.intent_node_id, "blocked")
            return DispatchOutcome(intent, tool="", ran=False,
                                   reason="budget épuisé — wrap-up forcé")

        # ── RL decision ──────────────────────────────────────────────────
        state = self._state(intent.target, intent.phase)
        decision = self.rl.next_action(self.task_id, state, intent.phase)
        tool, ah = self._resolve_tool(intent.phase, decision)
        if tool is None:
            self.graph.set_status(intent.intent_node_id, "failed")
            return DispatchOutcome(intent, tool=decision["tool"], ran=False,
                                   reason=f"aucun outil pour la phase {intent.phase}")

        # ── interception gate ────────────────────────────────────────────
        self._worker_seq += 1
        command = [tool.binary or tool.name, intent.target]
        decision_gate = self.interception.check(
            tool.name, command, tool.requires_interception
        )
        # Record every destructive / rule-matched decision in the audit trail.
        if tool.requires_interception or not decision_gate.allowed:
            det = decision_gate.detail or {}
            action = det.get("action")
            if decision_gate.allowed:
                status, decided_by = "allowed", det.get("decided_by", "system")
            elif action == "deny":
                status, decided_by = "denied", "rule"
            else:
                status, decided_by = "pending", None
            GLOBAL_APPROVALS.record(
                task_id=self.task_id, task_name=self.task_name, tool=tool.name,
                source=f"worker#{self._worker_seq}",
                matched_rule=decision_gate.reason,
                decision_source="rule" if decided_by == "rule" else "default",
                arguments={"command": " ".join(command), **intent.params},
                status=status, decided_by=decided_by,
            )
        if not decision_gate.allowed:
            self.graph.set_status(intent.intent_node_id, "pending_approval")
            return DispatchOutcome(intent, tool=tool.name, ran=False,
                                   reason="approbation humaine requise")

        # ── noise governor clamps the RL-proposed delay ──────────────────
        effective_delay = self.governor.clamp_delay(decision["delay"])

        # ── execute ──────────────────────────────────────────────────────
        self.graph.set_status(intent.intent_node_id, "running")
        if self.budget is not None:
            self.budget.charge(turns=1)
        result = await tool.run(
            intent.target, timing=decision["timing"], frag=decision["frag"],
            delay=effective_delay, **intent.params,
        )

        facts, findings, gain = self._write_back(intent, tool.name, result)
        reward = compute_reward(result, objective_gain=gain)
        self.rl.update(self.task_id, state, ah, reward.value, dict(state))
        self.graph.set_status(
            intent.intent_node_id, "done" if result.success else "failed"
        )
        return DispatchOutcome(
            intent=intent, tool=tool.name, ran=not result.skipped,
            reason="skipped (binaire absent)" if result.skipped else "",
            reward=reward.value, facts=facts, findings=findings,
            effective_delay_ms=effective_delay,
        )

    def _resolve_tool(self, phase: str, decision: dict[str, Any]):
        tool = self.registry.get(decision["tool"])
        if tool is not None and phase in tool.phases:
            return tool, decision["action_hash"]
        phase_tools = self.registry.for_phase(phase)
        if not phase_tools:
            return None, decision["action_hash"]
        tool = phase_tools[0]
        ah = action_hash(tool.name, decision["timing"], decision["delay"],
                         decision["frag"])
        if ah not in enumerate_action_hashes(phase):
            ah = decision["action_hash"]
        return tool, ah

    def _link_evidence(self, finding_node_id: str) -> str | None:
        if self.evidence is None:
            return None
        items = self.evidence.all()
        if not items:
            return None
        ev = items[-1]
        self.evidence.link_finding(ev.id, finding_node_id)
        return ev.id

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
                     "matched_at": f.get("matched_at"), "tool": tool_name,
                     "attack": attack_techniques(tool_name)},
                    agent="dispatcher",
                )
                self.graph.add_edge(fact.id, node.id, "proves")
                ev_id = self._link_evidence(node.id)
                if ev_id:
                    node.content["evidence_id"] = ev_id
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
