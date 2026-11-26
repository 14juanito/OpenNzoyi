"""Tool registry — name → Tool instance lookup for the dispatcher."""

from __future__ import annotations

from tools.base import Tool
from tools.implementations.nmap import NmapTool
from tools.implementations.nuclei import NucleiTool
from tools.implementations.netexec import NetexecTool


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
    """Phase 2 catalogue: nmap (recon), nuclei (vuln), netexec (ad_enum)."""
    reg = ToolRegistry()
    for tool in (NmapTool(), NucleiTool(), NetexecTool()):
        reg.register(tool)
    return reg
