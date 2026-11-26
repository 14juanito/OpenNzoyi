"""End-to-end loop test with fake tools (no binaries, no lab, no network).

Proves the Planner → Dispatcher → RL → graph write-back → report pipeline
produces a verifiable report with a severity-sorted finding.
"""

import asyncio

from engine import Engine
from tools.base import Tool, ToolResult
from tools.registry import ToolRegistry
from rl_client import RLClient


class FakeRecon(Tool):
    name = "nmap"
    phases = ("recon",)

    async def run(self, target, **params):
        return ToolResult(
            success=True, duration_ms=50,
            parsed={"hosts": [{"address": target, "ports": [
                {"port": 80, "service": "http", "product": "Apache"},
                {"port": 445, "service": "microsoft-ds", "product": "Windows"},
            ]}], "open_ports": [80, 445]},
        )

    def parse(self, stdout):
        return {}


class FakeVuln(Tool):
    name = "nuclei"
    phases = ("vuln",)

    async def run(self, target, **params):
        return ToolResult(
            success=True, duration_ms=120,
            parsed={"findings": [
                {"name": "Path Traversal", "severity": "high",
                 "matched_at": target, "template_id": "CVE-2021-41773"},
                {"name": "Apache Detect", "severity": "info", "matched_at": target},
            ], "count": 2},
        )

    def parse(self, stdout):
        return {}


class FakeAdEnum(Tool):
    name = "netexec"
    phases = ("ad_enum", "lateral")

    async def run(self, target, **params):
        return ToolResult(
            success=True, duration_ms=80,
            parsed={"hosts": [{"ip": target, "name": "DC01", "domain": "CORP"}],
                    "shares": [{"share": "SYSVOL", "perms": "READ"}]},
        )

    def parse(self, stdout):
        return {}


def _registry():
    reg = ToolRegistry()
    for t in (FakeRecon(), FakeVuln(), FakeAdEnum()):
        reg.register(t)
    return reg


def test_e2e_produces_report_with_findings():
    engine = Engine(registry=_registry(), rl_client=RLClient())  # in-process RL
    result = asyncio.run(
        engine.run(
            target="192.168.100.11",
            scope={"cidrs": ["192.168.100.0/24"], "domains": []},
            name="lab-audit",
        )
    )
    rep = result.report()

    # recon ran, services discovered, assets recorded
    assert rep["summary"]["assets"] >= 1
    assert rep["summary"]["facts"] >= 2  # recon + vuln (+ ad_enum)

    # at least the high finding, sorted first
    assert rep["summary"]["findings_total"] >= 1
    assert rep["findings"][0]["severity"] == "high"
    assert rep["findings"][0]["title"] == "Path Traversal"

    # every step stayed in scope and actually ran
    assert all(o.ran for o in result.outcomes)
    # graph provenance: a 'proves' edge links fact → finding
    assert any(e["relation"] == "proves" for e in rep["graph"]["edges"])


def test_e2e_out_of_scope_target_refused():
    """A target outside the declared scope is refused by the dispatcher."""
    engine = Engine(registry=_registry(), rl_client=RLClient())
    result = asyncio.run(
        engine.run(
            target="10.0.0.5",  # scope only covers 192.168.100.0/24
            scope={"cidrs": ["192.168.100.0/24"], "domains": []},
        )
    )
    # recon intent on the seeded asset (10.0.0.5) is out of scope → refused
    assert any(not o.ran and "hors scope" in o.reason for o in result.outcomes)
