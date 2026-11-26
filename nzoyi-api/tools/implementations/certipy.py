"""certipy wrapper — AD CS enumeration / abuse (post phase).

``find`` (enumeration) runs by default and is read-only. Exploitation commands
(``req``, ``auth``, ``ca``) are destructive and flagged for the interception
gate.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_VULN_RE = re.compile(r"ESC(?P<n>\d+)")
_SAFE = {"find"}


class CertipyTool(Tool):
    name = "certipy"
    binary = "certipy"
    phases = ("post",)

    def __init__(self, command: str = "find") -> None:
        self.command = command
        self.requires_interception = command not in _SAFE

    async def run(
        self, target: str, domain: str = "", username: str = "", password: str = "",
        extra: list[str] | None = None, timeout: int = 300, **_: Any,
    ) -> ToolResult:
        cmd = ["certipy", self.command, "-dc-ip", target]
        if username:
            cmd += ["-u", f"{username}@{domain}" if domain else username, "-p", password]
        if self.command == "find":
            cmd += ["-vulnerable", "-stdout"]
        cmd += extra or []
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        esc = sorted({f"ESC{m.group('n')}" for m in _VULN_RE.finditer(stdout)})
        return {"command": self.command, "vulnerable_templates": esc}
