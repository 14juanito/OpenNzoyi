"""sdn-toolkit wrapper — SDN flow inspection / evasion (evasion phase).

Reads OpenFlow flow tables (via ovs-ofctl or a controller helper) to observe
whether the SDN has installed block/quarantine flows against the attacker — the
``sdn_flow_blocks`` RL state dimension. Flow *modification* is gated.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_FLOW_RE = re.compile(r"actions=(?P<act>drop|CONTROLLER|output)", re.I)


class SdnToolkitTool(Tool):
    name = "sdn-toolkit"
    binary = "ovs-ofctl"
    phases = ("evasion",)

    def __init__(self, action: str = "dump-flows") -> None:
        self.action = action
        self.requires_interception = action not in {"dump-flows", "show"}

    async def run(self, target: str = "br0", extra: list[str] | None = None,
                  timeout: int = 60, **_: Any) -> ToolResult:
        cmd = ["ovs-ofctl", self.action, target] + (extra or [])
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=self.parse(r.stdout), duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        drops = sum(1 for m in _FLOW_RE.finditer(stdout) if m.group("act").lower() == "drop")
        total = len(stdout.strip().splitlines())
        return {"flow_count": total, "drop_flows": drops}
