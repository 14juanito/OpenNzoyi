"""nmap wrapper — network/service discovery (recon phase)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess

# Nmap timing templates mapped from the RL action space (T1..T4 -> -T2..-T5).
_TIMING_MAP = {"T1": "2", "T2": "3", "T3": "4", "T4": "5"}


class NmapTool(Tool):
    name = "nmap"
    binary = "nmap"
    phases = ("recon",)
    requires_interception = False

    async def run(
        self,
        target: str,
        timing: str = "T2",
        frag: bool = False,
        ports: str | None = None,
        timeout: int = 600,
        **_: Any,
    ) -> ToolResult:
        cmd = ["nmap", "-sV", "-T", _TIMING_MAP.get(timing, "3"), "-oX", "-"]
        if frag:
            cmd.append("-f")
        if ports:
            cmd += ["-p", ports]
        cmd.append(target)

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
        try:
            root = ET.fromstring(stdout)
        except ET.ParseError:
            return {"hosts": [], "open_ports": []}
        open_ports: list[int] = []
        for host in root.findall("host"):
            addr_el = host.find("address")
            addr = addr_el.get("addr") if addr_el is not None else ""
            ports: list[dict[str, Any]] = []
            for port in host.findall("./ports/port"):
                state_el = port.find("state")
                state = state_el.get("state") if state_el is not None else "unknown"
                if state != "open":
                    continue
                svc = port.find("service")
                portid = int(port.get("portid", "0"))
                open_ports.append(portid)
                ports.append(
                    {
                        "port": portid,
                        "protocol": port.get("protocol", "tcp"),
                        "state": state,
                        "service": (svc.get("name") if svc is not None else "") or "",
                        "product": (svc.get("product") if svc is not None else "") or "",
                        "version": (svc.get("version") if svc is not None else "") or "",
                    }
                )
            hosts.append({"address": addr, "ports": ports})
        return {"hosts": hosts, "open_ports": sorted(set(open_ports))}
