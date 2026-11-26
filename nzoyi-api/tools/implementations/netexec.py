"""netexec (nxc) wrapper — SMB/AD enumeration (ad_enum phase).

Enumeration only in this wrapper (shares, sessions, null/guest checks). Any
credentialed or destructive module (e.g. --sam, dcsync) is routed through the
interception gate (Phase 4); this wrapper exposes read-only recon by default.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

# "SMB  10.0.0.1  445  HOST  [*] Windows 10 ... (name:HOST) (domain:CORP) ..."
_HOST_RE = re.compile(
    r"^SMB\s+(?P<ip>\S+)\s+(?P<port>\d+)\s+(?P<name>\S+)\s+\[\*\]\s+(?P<os>.+)$"
)
_SIGNED_RE = re.compile(r"\(signing:(?P<signing>\w+)\)")
_DOMAIN_RE = re.compile(r"\(domain:(?P<domain>[^)]+)\)")
_SHARE_RE = re.compile(
    r"^SMB\s+\S+\s+\d+\s+\S+\s+(?P<share>\S+)\s+(?P<perms>READ|WRITE|READ,WRITE)?",
)


class NetexecTool(Tool):
    name = "netexec"
    binary = "nxc"
    phases = ("ad_enum", "lateral")
    requires_interception = False

    async def run(
        self,
        target: str,
        protocol: str = "smb",
        username: str = "",
        password: str = "",
        module: str | None = None,
        timeout: int = 300,
        **_: Any,
    ) -> ToolResult:
        cmd = ["nxc", protocol, target]
        if username:
            cmd += ["-u", username, "-p", password]
        else:
            cmd += ["-u", "", "-p", ""]  # null session enumeration
        if module:
            cmd += ["-M", module]
        else:
            cmd.append("--shares")

        r = await run_subprocess(cmd, timeout=timeout)
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
        hosts: list[dict[str, Any]] = []
        shares: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.rstrip()
            m = _HOST_RE.match(line)
            if m:
                os_field = m.group("os")
                dm = _DOMAIN_RE.search(os_field)
                sm = _SIGNED_RE.search(os_field)
                hosts.append(
                    {
                        "ip": m.group("ip"),
                        "port": int(m.group("port")),
                        "name": m.group("name"),
                        "os": os_field.strip(),
                        "domain": dm.group("domain") if dm else None,
                        "signing": sm.group("signing") if sm else None,
                    }
                )
                continue
            if "[*]" in line or "[+]" in line or "[-]" in line:
                continue
            sm2 = _SHARE_RE.match(line)
            if sm2 and sm2.group("perms"):
                shares.append(
                    {"share": sm2.group("share"), "perms": sm2.group("perms")}
                )
        return {"hosts": hosts, "shares": shares}
