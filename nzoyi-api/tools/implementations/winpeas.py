"""winPEAS wrapper — Windows privilege-escalation enumeration (post phase)."""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}")
# winPEAS marks interesting findings in red; without colour, "[!]" prefixes them.
_HIT_RE = re.compile(r"^\s*\[!\]\s*(?P<detail>.+)$")


class WinpeasTool(Tool):
    name = "winpeas"
    binary = "winpeas.exe"
    phases = ("post",)

    async def run(self, target: str = "", timeout: int = 600, **_: Any) -> ToolResult:
        cmd = ["winpeas.exe", "log"]
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=self.parse(r.stdout), duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        vectors = [m.group("detail").strip()[:200]
                   for line in stdout.splitlines()
                   if (m := _HIT_RE.match(line))]
        return {"pe_vectors": vectors, "cves": sorted(set(_CVE_RE.findall(stdout))),
                "count": len(vectors)}
