"""nikto wrapper — web server misconfiguration scan (vuln phase)."""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_OSVDB_RE = re.compile(r"(OSVDB-\d+|CVE-\d{4}-\d+)")


class NiktoTool(Tool):
    name = "nikto"
    binary = "nikto"
    phases = ("vuln",)

    async def run(self, target: str, proxy: str | None = None, timeout: int = 900, **_: Any) -> ToolResult:
        cmd = ["nikto", "-h", target, "-ask", "no", "-nointeractive"]
        if proxy:
            cmd += ["-useproxy", proxy]
        r = await run_subprocess(cmd, timeout=timeout, proxy=proxy)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line.startswith("+ "):
                continue
            desc = line[2:].strip()
            refs = _OSVDB_RE.findall(desc)
            items.append({"message": desc, "refs": refs})
        return {"items": items, "count": len(items)}
