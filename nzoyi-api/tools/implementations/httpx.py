"""httpx wrapper — HTTP probing / fingerprinting (recon phase)."""

from __future__ import annotations

import json
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess


class HttpxTool(Tool):
    name = "httpx"
    binary = "httpx"
    phases = ("recon",)

    async def run(self, target: str, proxy: str | None = None, timeout: int = 300, **_: Any) -> ToolResult:
        cmd = ["httpx", "-u", target, "-json", "-silent",
               "-status-code", "-title", "-tech-detect", "-no-color"]
        if proxy:
            cmd += ["-http-proxy", proxy]
        r = await run_subprocess(cmd, timeout=timeout, proxy=proxy)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        urls: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            urls.append({
                "url": obj.get("url") or obj.get("input"),
                "status_code": obj.get("status_code") or obj.get("status-code"),
                "title": obj.get("title"),
                "tech": obj.get("tech") or obj.get("technologies") or [],
                "webserver": obj.get("webserver"),
            })
        return {"urls": urls, "count": len(urls)}
