"""rustscan wrapper — fast port sweep (recon phase)."""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_OPEN_RE = re.compile(r"Open\s+(?P<ip>[\d.]+):(?P<port>\d+)")


class RustscanTool(Tool):
    name = "rustscan"
    binary = "rustscan"
    phases = ("recon",)

    async def run(self, target: str, timing: str = "T2", timeout: int = 300, **_: Any) -> ToolResult:
        # Batch size scales (loosely) with the RL timing template.
        batch = {"T1": "500", "T2": "1500", "T3": "3000", "T4": "4500"}.get(timing, "1500")
        cmd = ["rustscan", "-a", target, "-b", batch, "--greppable"]
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        ports = sorted({int(m.group("port")) for m in _OPEN_RE.finditer(stdout)})
        return {"open_ports": ports, "count": len(ports)}
