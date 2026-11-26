"""chisel wrapper — TCP/UDP tunnelling for pivoting (lateral phase).

Unlike scanners, chisel establishes a persistent tunnel. ``run`` starts the
client for a bounded probe window and reports whether the tunnel connected; the
long-lived tunnel is managed by the lateral-movement agent (Phase 3+). Creating
a pivot is a high-signal action, hence ``requires_interception``.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_CONN_RE = re.compile(r"Connected|tunnel.*open|Fingerprint", re.I)


class ChiselTool(Tool):
    name = "chisel"
    binary = "chisel"
    phases = ("lateral",)
    requires_interception = True

    async def run(
        self, target: str, server: str = "", remote: str = "", mode: str = "client",
        probe_seconds: int = 5, **_: Any,
    ) -> ToolResult:
        if mode == "client":
            cmd = ["chisel", "client", server or target, remote or "R:socks"]
        else:
            cmd = ["chisel", "server", "--reverse", "--port", "8080"]
        # Bounded probe: we only need to confirm the tunnel establishes.
        r = await run_subprocess(cmd, timeout=probe_seconds)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout + "\n" + r.stderr)
        # A timeout here is expected (tunnel stays open); treat connected as success.
        return ToolResult(success=parsed["connected"], stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        return {"connected": bool(_CONN_RE.search(stdout))}
