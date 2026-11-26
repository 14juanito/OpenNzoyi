"""nuclei wrapper — templated vulnerability scanning (vuln phase)."""

from __future__ import annotations

import json
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

_SEV_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class NucleiTool(Tool):
    name = "nuclei"
    binary = "nuclei"
    phases = ("vuln",)
    requires_interception = False

    async def run(
        self,
        target: str,
        severity: str = "medium,high,critical",
        proxy: str | None = None,
        timeout: int = 600,
        **_: Any,
    ) -> ToolResult:
        cmd = [
            "nuclei", "-u", target, "-severity", severity,
            "-jsonl", "-silent", "-timeout", "10",
        ]
        if proxy:
            cmd += ["-proxy", proxy]
        r = await run_subprocess(cmd, timeout=timeout, proxy=proxy)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(
            success=r.returncode == 0,
            stdout=r.stdout,
            stderr=r.stderr,
            parsed=parsed,
            duration_ms=r.duration_ms,
        )

    def parse(self, stdout: str) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            info = obj.get("info", {}) if isinstance(obj, dict) else {}
            findings.append(
                {
                    "template_id": obj.get("template-id") or obj.get("templateID"),
                    "name": info.get("name"),
                    "severity": (info.get("severity") or "info").lower(),
                    "matched_at": obj.get("matched-at") or obj.get("matched_at")
                    or obj.get("host"),
                    "type": obj.get("type"),
                }
            )
        findings.sort(
            key=lambda f: _SEV_ORDER.get(f.get("severity", "info"), 0), reverse=True
        )
        return {"findings": findings, "count": len(findings)}
