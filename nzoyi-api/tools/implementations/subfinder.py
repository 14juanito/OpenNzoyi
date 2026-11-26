"""subfinder wrapper — passive subdomain enumeration (recon phase)."""

from __future__ import annotations

import json
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess


class SubfinderTool(Tool):
    name = "subfinder"
    binary = "subfinder"
    phases = ("recon",)

    async def run(self, target: str, timeout: int = 300, **_: Any) -> ToolResult:
        cmd = ["subfinder", "-d", target, "-silent", "-json"]
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        subs: list[str] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                host = obj.get("host") or obj.get("subdomain")
            except json.JSONDecodeError:
                host = line  # plain -silent output
            if host:
                subs.append(host)
        subs = sorted(set(subs))
        return {"subdomains": subs, "count": len(subs)}
