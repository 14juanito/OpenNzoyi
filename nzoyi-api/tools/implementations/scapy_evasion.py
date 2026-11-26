"""scapy/iodine evasion wrapper — covert channels & packet shaping (evasion).

Covers the evasion-phase action-space tools ``scapy_frag`` (fragmented/crafted
delivery) and ``iodine`` (DNS tunnelling). Establishing a covert channel is
high-signal — gated. The wrapper invokes the operator-provided tooling; it does
not embed packet payloads.
"""

from __future__ import annotations

from typing import Any

from tools.base import Tool, ToolResult
from tools.runner import run_subprocess


class ScapyEvasionTool(Tool):
    name = "scapy_evasion"
    binary = "iodine"
    phases = ("evasion",)
    requires_interception = True

    def __init__(self, mode: str = "iodine") -> None:
        self.mode = mode  # "iodine" (DNS tunnel) | "frag" (scapy script)

    async def run(
        self, target: str, nameserver: str = "", password: str = "",
        script: str = "", timeout: int = 60, **_: Any,
    ) -> ToolResult:
        if self.mode == "frag":
            cmd = ["python3", script or "scapy_frag.py", target]
            self.binary = "python3"
        else:
            cmd = ["iodine", "-f", nameserver or target]
            if password:
                cmd += ["-P", password]
        r = await run_subprocess(cmd, timeout=timeout)
        if not r.found:
            return ToolResult(success=False, skipped=True, stderr=r.stderr)
        return ToolResult(success=r.returncode == 0, stdout=r.stdout, stderr=r.stderr,
                          parsed=self.parse(r.stdout), duration_ms=r.duration_ms)

    def parse(self, stdout: str) -> dict[str, Any]:
        established = "Connection setup complete" in stdout or "sending" in stdout.lower()
        return {"mode": self.mode, "channel_established": established}
