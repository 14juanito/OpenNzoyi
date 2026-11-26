"""linPEAS wrapper — Linux privilege-escalation enumeration (linux phase).

Runs on the compromised Linux host (local enumeration). The orchestrator ships
and executes it through the session channel; the wrapper parses the high-signal
PE vectors (99%/95% probability tags and CVE references) out of the noisy output.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

# linPEAS strips colours with -a/NO_COLOR; tag lines look like "95% ..." / "99% ...".
_PROB_RE = re.compile(r"(?<!\d)(?P<p>9[59])%")
_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}")


class LinpeasTool(Tool):
    name = "linpeas"
    binary = "linpeas.sh"
    phases = ("linux",)

    async def run(self, target: str = "localhost", timeout: int = 600, **_: Any) -> ToolResult:
        cmd = ["linpeas.sh", "-a"]
        r = await run_subprocess(cmd, timeout=timeout, env_extra={"NO_COLOR": "1"})
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        vectors: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            pm = _PROB_RE.search(line)
            if pm:
                vectors.append({"probability": int(pm.group("p")),
                                "detail": line.strip()[:200]})
        cves = sorted(set(_CVE_RE.findall(stdout)))
        return {"pe_vectors": vectors, "cves": cves, "count": len(vectors)}
