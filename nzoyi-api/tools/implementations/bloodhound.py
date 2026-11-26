"""bloodhound wrapper — AD graph collection via bloodhound-python (ad_enum)."""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_COUNT_RE = re.compile(r"Found (?P<n>\d+) (?P<kind>users|computers|groups|domains)", re.I)


class BloodHoundTool(Tool):
    name = "bloodhound"
    binary = "bloodhound-python"
    phases = ("ad_enum",)

    async def run(
        self, target: str, domain: str = "", username: str = "", password: str = "",
        nameserver: str | None = None, timeout: int = 600, **_: Any,
    ) -> ToolResult:
        cmd = ["bloodhound-python", "-d", domain, "-u", username, "-p", password,
               "-c", "DCOnly", "--zip"]
        if nameserver:
            cmd += ["-ns", nameserver]
        else:
            cmd += ["-dc", target]
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout + "\n" + r.stderr)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for m in _COUNT_RE.finditer(stdout):
            counts[m.group("kind").lower()] = int(m.group("n"))
        return {"collected": counts}
