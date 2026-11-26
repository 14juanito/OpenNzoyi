"""Tool contract for the NZOYI offensive catalogue.

Every offensive capability is a :class:`Tool`: a thin, auditable wrapper that
shells out to a standard security binary (nmap, nuclei, netexec, …) and parses
its output into a structured ``ToolResult``. Wrappers never embed exploit
payloads or credentials — they orchestrate binaries the operator installs in the
authorised lab.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Normalized result of a single tool invocation."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    parsed: dict[str, Any] = field(default_factory=dict)
    evidence_id: str | None = None
    duration_ms: int = 0
    # Filled a posteriori by the EvaluationAgent from IDS/EDR telemetry.
    alerts_generated: int = 0
    # Set when the binary was not found / not executed (distinct from a run
    # that executed and failed).
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "skipped": self.skipped,
            "parsed": self.parsed,
            "evidence_id": self.evidence_id,
            "duration_ms": self.duration_ms,
            "alerts_generated": self.alerts_generated,
            "stderr": self.stderr[-2000:] if self.stderr else "",
        }


class Tool(ABC):
    """Abstract base class for an offensive tool wrapper."""

    name: str = "tool"
    binary: str = ""
    #: Phases (see evasion.action.TOOLS_BY_PHASE) this tool belongs to.
    phases: tuple[str, ...] = ()
    #: Destructive/high-signal tools require human approval when the task runs
    #: in semi-autonomous mode (enforced by the interception gate, Phase 4).
    requires_interception: bool = False

    @abstractmethod
    async def run(self, target: str, **params: Any) -> ToolResult:
        """Execute the tool against ``target`` and return a ``ToolResult``."""

    @abstractmethod
    def parse(self, stdout: str) -> dict[str, Any]:
        """Parse raw stdout into a structured dict. Must never raise."""
