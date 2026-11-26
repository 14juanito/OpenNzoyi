"""Tool registry — name → Tool instance lookup for the dispatcher."""

from __future__ import annotations

from tools.base import Tool
from tools.implementations.nmap import NmapTool
from tools.implementations.rustscan import RustscanTool
from tools.implementations.httpx import HttpxTool
from tools.implementations.subfinder import SubfinderTool
from tools.implementations.nuclei import NucleiTool
from tools.implementations.ffuf import FfufTool
from tools.implementations.sqlmap import SqlmapTool
from tools.implementations.nikto import NiktoTool
from tools.implementations.netexec import NetexecTool
from tools.implementations.impacket import ImpacketTool
from tools.implementations.bloodhound import BloodHoundTool
from tools.implementations.sharphound import SharpHoundTool
from tools.implementations.linpeas import LinpeasTool
from tools.implementations.linux_exploit_suggester import LinuxExploitSuggesterTool
from tools.implementations.chisel import ChiselTool


class ToolRegistry:
    """Holds the available tools and resolves them by name or phase."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def for_phase(self, phase: str) -> list[Tool]:
        return [t for t in self._tools.values() if phase in t.phases]


def default_registry() -> ToolRegistry:
    """Full P0 + P1 catalogue (Phase 2–3).

    Tools whose binary is absent degrade to ``skipped`` at run time, so the
    registry can list everything while the host installs only part of the
    toolchain.
    """
    reg = ToolRegistry()
    tools = [
        # recon
        NmapTool(), RustscanTool(), HttpxTool(), SubfinderTool(),
        # vuln
        NucleiTool(), FfufTool(), SqlmapTool(), NiktoTool(),
        # ad_enum
        NetexecTool(), ImpacketTool(), BloodHoundTool(), SharpHoundTool(),
        # linux priv-esc
        LinpeasTool(), LinuxExploitSuggesterTool(),
        # lateral
        ChiselTool(),
    ]
    for tool in tools:
        reg.register(tool)
    return reg
