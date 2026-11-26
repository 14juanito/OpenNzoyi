"""sharphound wrapper — AD collection (runs on the Windows target).

SharpHound is the C# collector executed on a Windows host; the orchestrator
invokes it through the lateral-movement exec channel. This wrapper normalises
its console output (object counts) and the produced zip path. On a Linux
orchestrator without the collector present, it degrades to ``skipped``.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_OBJ_RE = re.compile(r"(?P<n>\d+)\s+objects?", re.I)
_ZIP_RE = re.compile(r"(\S+\.zip)")


class SharpHoundTool(Tool):
    name = "sharphound"
    binary = "sharphound"
    phases = ("ad_enum",)

    async def run(self, target: str, collection: str = "Default", timeout: int = 600, **_: Any) -> ToolResult:
        cmd = ["sharphound", "-c", collection, "-d", target]
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        m = _OBJ_RE.search(stdout)
        z = _ZIP_RE.search(stdout)
        return {
            "objects": int(m.group("n")) if m else 0,
            "zip": z.group(1) if z else None,
        }
