"""Rubeus wrapper — Kerberos abuse on the Windows target (post phase).

Rubeus.exe runs on the compromised Windows host via the exec channel. Kerberoast
/ asreproast / ticket operations are credential-affecting — always gated.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_HASH_RE = re.compile(r"\$krb5(tgs|asrep)\$")


class RubeusTool(Tool):
    name = "rubeus"
    binary = "rubeus"
    phases = ("post",)
    requires_interception = True

    def __init__(self, command: str = "kerberoast") -> None:
        self.command = command

    async def run(self, target: str = "", extra: list[str] | None = None,
                  timeout: int = 180, **_: Any) -> ToolResult:
        cmd = ["rubeus", self.command, "/nowrap"] + (extra or [])
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=self.parse(r.stdout), duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        tickets = len(_HASH_RE.findall(stdout))
        return {"command": self.command, "tickets": tickets}
