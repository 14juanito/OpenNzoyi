"""ffuf wrapper — content/endpoint fuzzing (vuln phase)."""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

# ".git/config            [Status: 200, Size: 92, Words: 3, Lines: 4, Duration: 5ms]"
_HIT_RE = re.compile(
    r"^(?P<word>\S+)\s+\[Status:\s*(?P<status>\d+),\s*Size:\s*(?P<size>\d+)"
)


class FfufTool(Tool):
    name = "ffuf"
    binary = "ffuf"
    phases = ("vuln",)

    async def run(
        self,
        target: str,
        wordlist: str = "/usr/share/seclists/Discovery/Web-Content/common.txt",
        proxy: str | None = None,
        timeout: int = 600,
        **_: Any,
    ) -> ToolResult:
        url = target if "FUZZ" in target else target.rstrip("/") + "/FUZZ"
        cmd = ["ffuf", "-u", url, "-w", wordlist, "-mc", "200,204,301,302,307,401,403",
               "-noninteractive"]
        if proxy:
            cmd += ["-x", proxy]
        r = await run_subprocess(cmd, timeout=timeout, proxy=proxy)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        hits: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            m = _HIT_RE.match(line.strip())
            if m:
                hits.append({
                    "path": m.group("word"),
                    "status": int(m.group("status")),
                    "size": int(m.group("size")),
                })
        return {"hits": hits, "count": len(hits)}
