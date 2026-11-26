"""Approval records — audit trail of interception decisions.

Every time the interception gate evaluates a destructive / rule-matched tool
call, a record is written here: what tool, from which task/worker, which rule
matched, the arguments, the decision (allowed / denied / pending) and who
decided (human / rule / model / system). In semi-autonomous mode a destructive
action is recorded as ``pending`` until a human decides via :meth:`decide`.

Mirrors the ``approvals`` / ``approval_rules`` tables (Phase 1).
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_now = lambda: datetime.now(timezone.utc).isoformat()


@dataclass
class ApprovalRecord:
    seq: int
    task_id: str
    task_name: str
    tool: str
    source: str            # e.g. "worker#3"
    matched_rule: str      # human-readable rule / reason
    decision_source: str   # "rule" | "model_decision" | "default"
    arguments: dict[str, Any]
    status: str            # "allowed" | "denied" | "pending"
    decided_by: str | None  # "human" | "rule" | "model" | "system" | None
    requested_at: str = field(default_factory=_now)
    decided_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "tool": self.tool,
            "source": self.source,
            "matched_rule": self.matched_rule,
            "decision_source": self.decision_source,
            "arguments": self.arguments,
            "status": self.status,
            "decided_by": self.decided_by,
            "requested_at": self.requested_at,
            "decided_at": self.decided_at,
        }


class ApprovalStore:
    def __init__(self) -> None:
        self._records: dict[int, ApprovalRecord] = {}
        self._seq = itertools.count(1)
        self._lock = threading.RLock()

    def record(
        self,
        task_id: str,
        task_name: str,
        tool: str,
        source: str,
        matched_rule: str,
        decision_source: str,
        arguments: dict[str, Any],
        status: str,
        decided_by: str | None,
    ) -> ApprovalRecord:
        with self._lock:
            rec = ApprovalRecord(
                seq=next(self._seq), task_id=task_id, task_name=task_name,
                tool=tool, source=source, matched_rule=matched_rule,
                decision_source=decision_source, arguments=arguments,
                status=status, decided_by=decided_by,
                decided_at=_now() if status != "pending" else None,
            )
            self._records[rec.seq] = rec
            return rec

    def decide(self, seq: int, status: str, decided_by: str = "human") -> ApprovalRecord | None:
        with self._lock:
            rec = self._records.get(seq)
            if rec is None or rec.status != "pending":
                return rec
            rec.status = status           # "allowed" | "denied"
            rec.decided_by = decided_by
            rec.decided_at = _now()
            return rec

    def all(self) -> list[ApprovalRecord]:
        with self._lock:
            return sorted(self._records.values(), key=lambda r: r.seq, reverse=True)

    def pending(self) -> list[ApprovalRecord]:
        return [r for r in self.all() if r.status == "pending"]


# Process-wide store shared by the dispatcher and the HTTP API.
GLOBAL_APPROVALS = ApprovalStore()
