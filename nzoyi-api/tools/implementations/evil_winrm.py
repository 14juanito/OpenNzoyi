"""evil-winrm wrapper — WinRM remote shell (lateral/post phase).

Remote command execution over WinRM — destructive, always gated. A single
command is passed non-interactively; the long interactive shell is managed by
the lateral agent.
"""

from __future__ import annotations

from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess


class EvilWinrmTool(Tool):
    name = "evil-winrm"
    binary = "evil-winrm"
    phases = ("lateral", "post")
    requires_interception = True

    async def run(
        self, target: str, username: str = "", password: str = "",
        command: str = "whoami", hash: str = "", timeout: int = 120, **_: Any,
    ) -> ToolResult:
        cmd = ["evil-winrm", "-i", target, "-u", username]
        if hash:
            cmd += ["-H", hash]
        elif password:
            cmd += ["-p", password]
        # Pipe the command through stdin is interactive; use -c when available.
        cmd += ["-c", command] if command else []
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=self.parse(r.stdout), duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        return {"output": stdout.strip()[:2000]}
