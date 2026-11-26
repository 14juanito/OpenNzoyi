"""Niveau 2 — worker sous-agent : chaînage multi-outils par intent."""

import asyncio

from engine import Engine
from tools.base import Tool, ToolResult
from tools.registry import ToolRegistry
from rl_client import RLClient


class FakeRecon(Tool):
    name = "nmap"
    phases = ("recon",)
    async def run(self, target, **p):
        return ToolResult(success=True, duration_ms=10,
                          parsed={"hosts": [{"address": target, "ports": [
                              {"port": 80, "service": "http", "product": "Apache"}]}],
                                  "open_ports": [80]})
    def parse(self, s): return {}


class _Vuln(Tool):
    phases = ("vuln",)
    async def run(self, target, **p):
        return ToolResult(success=True, duration_ms=10,
                          parsed={"findings": [{"name": f"F-{self.name}", "severity": "high",
                                                "matched_at": target}], "count": 1})
    def parse(self, s): return {}


class FakeNuclei(_Vuln): name = "nuclei"
class FakeFfuf(_Vuln): name = "ffuf"


def _registry():
    r = ToolRegistry()
    for t in (FakeRecon(), FakeNuclei(), FakeFfuf()):
        r.register(t)
    return r


def test_worker_chains_multiple_tools_in_vuln_phase():
    engine = Engine(registry=_registry(), rl_client=RLClient())
    result = asyncio.run(engine.run(
        target="192.168.100.11",
        scope={"cidrs": ["192.168.100.0/24"], "domains": []}))
    # find a vuln outcome and assert the worker ran BOTH vuln tools (chain)
    vuln = [o for o in result.outcomes if o.intent.phase == "vuln"]
    assert vuln, "no vuln intent dispatched"
    tools_run = {s["tool"] for o in vuln for s in o.steps if s["ran"]}
    assert {"nuclei", "ffuf"} <= tools_run, tools_run  # chained multiple tools


def test_worker_recon_stops_after_result():
    engine = Engine(registry=_registry(), rl_client=RLClient())
    result = asyncio.run(engine.run(
        target="192.168.100.11",
        scope={"cidrs": ["192.168.100.0/24"], "domains": []}))
    recon = [o for o in result.outcomes if o.intent.phase == "recon"][0]
    # recon stops after a productive step (no spamming)
    assert len([s for s in recon.steps if s["ran"]]) == 1
