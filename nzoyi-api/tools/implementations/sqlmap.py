"""sqlmap wrapper — SQL injection detection (vuln phase).

Detection-oriented by default (``--batch`` non-interactive, no dump). Data
exfiltration flags (--dump, --os-shell) are destructive and routed through the
interception gate (Phase 4); this wrapper does not enable them.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_PARAM_RE = re.compile(r"Parameter:\s*(?P<param>.+?)\s*\((?P<place>\w+)\)")
_TYPE_RE = re.compile(r"Type:\s*(?P<type>.+)")
_VULN_RE = re.compile(r"is vulnerable|sqlmap identified the following injection")


class SqlmapTool(Tool):
    name = "sqlmap"
    binary = "sqlmap"
    phases = ("vuln",)
    requires_interception = False

    async def run(
        self, target: str, data: str | None = None, proxy: str | None = None,
        timeout: int = 900, **_: Any,
    ) -> ToolResult:
        cmd = ["sqlmap", "-u", target, "--batch", "--level", "2", "--risk", "1",
               "--answers", "quit=N", "--flush-session"]
        if data:
            cmd += ["--data", data]
        if proxy:
            cmd += ["--proxy", proxy]
        r = await run_subprocess(cmd, timeout=timeout, proxy=proxy)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        vulnerable = bool(_VULN_RE.search(stdout))
        params: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for line in stdout.splitlines():
            pm = _PARAM_RE.search(line)
            if pm:
                current = {"parameter": pm.group("param"), "place": pm.group("place"),
                           "types": []}
                params.append(current)
                continue
            tm = _TYPE_RE.search(line)
            if tm and current is not None:
                current["types"].append(tm.group("type").strip())
        return {"vulnerable": vulnerable, "injection_points": params}
