"""impacket wrapper — AD enumeration / lateral movement example scripts.

Generic launcher for impacket's example scripts. Enumeration scripts are
read-only and run by default; credentialed/destructive scripts (secretsdump =
DCSync, wmiexec/psexec = remote exec) are flagged ``requires_interception`` so
the gate (Phase 4) forces an approval before they run.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

# script -> (binary candidates, destructive?)
_SCRIPTS = {
    "GetADUsers": (["impacket-GetADUsers", "GetADUsers.py"], False),
    "GetUserSPNs": (["impacket-GetUserSPNs", "GetUserSPNs.py"], False),
    "GetNPUsers": (["impacket-GetNPUsers", "GetNPUsers.py"], False),
    "secretsdump": (["impacket-secretsdump", "secretsdump.py"], True),
    "wmiexec": (["impacket-wmiexec", "wmiexec.py"], True),
    "psexec": (["impacket-psexec", "psexec.py"], True),
}

_SPN_RE = re.compile(r"\$krb5tgs\$")
_HASH_RE = re.compile(r"^[^:]+:\d+:[0-9a-f]{32}:[0-9a-f]{32}:::", re.I)


class ImpacketTool(Tool):
    name = "impacket"
    binary = "impacket-GetADUsers"
    phases = ("ad_enum", "lateral")

    def __init__(self, script: str = "GetADUsers") -> None:
        self.script = script
        self.requires_interception = _SCRIPTS.get(script, (None, True))[1]

    async def run(
        self, target: str, domain: str = "", username: str = "", password: str = "",
        extra: list[str] | None = None, timeout: int = 300, **_: Any,
    ) -> ToolResult:
        candidates, _ = _SCRIPTS.get(self.script, ([self.script], True))
        import shutil

        binary = next((c for c in candidates if shutil.which(c)), candidates[0])
        creds = f"{domain}/{username}:{password}@{target}" if username else f"{target}"
        cmd = [binary, creds] + (extra or [])
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        parsed = self.parse(r.stdout)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=parsed, duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        tickets = [ln for ln in stdout.splitlines() if _SPN_RE.search(ln)]
        hashes = [ln.strip() for ln in stdout.splitlines() if _HASH_RE.match(ln.strip())]
        return {
            "script": self.script,
            "kerberoast_tickets": len(tickets),
            "secrets_extracted": len(hashes),
        }
