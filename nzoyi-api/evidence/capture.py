"""Evidence store — captured request/response pairs linked to findings.

Every finding must carry a captured proof (mission brief, acceptance criteria).
The MITM proxy (``mitm_proxy.py``) feeds flows here; the store mirrors the
``evidence`` table (Phase 1) and returns an ``evidence_id`` the dispatcher
attaches to the finding node. In-memory for now; a PG-backed variant persists to
the ``evidence`` table.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Evidence:
    id: str
    task_id: str | None
    request_method: str | None
    request_url: str | None
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: bytes = b""
    response_status: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: bytes = b""
    finding_node_id: str | None = None
    captured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self, include_body: bool = False) -> dict[str, Any]:
        d = {
            "id": self.id,
            "task_id": self.task_id,
            "request": {
                "method": self.request_method,
                "url": self.request_url,
                "headers": self.request_headers,
            },
            "response": {
                "status": self.response_status,
                "headers": self.response_headers,
            },
            "finding_node_id": self.finding_node_id,
            "captured_at": self.captured_at,
        }
        if include_body:
            d["request"]["body"] = self.request_body.decode("utf-8", "replace")
            d["response"]["body"] = self.response_body.decode("utf-8", "replace")
        return d


class EvidenceStore:
    def __init__(self) -> None:
        self._by_id: dict[str, Evidence] = {}

    def capture(
        self,
        task_id: str | None,
        request_method: str | None,
        request_url: str | None,
        request_headers: dict[str, str] | None = None,
        request_body: bytes = b"",
        response_status: int | None = None,
        response_headers: dict[str, str] | None = None,
        response_body: bytes = b"",
    ) -> str:
        ev = Evidence(
            id=str(uuid.uuid4()),
            task_id=task_id,
            request_method=request_method,
            request_url=request_url,
            request_headers=request_headers or {},
            request_body=request_body,
            response_status=response_status,
            response_headers=response_headers or {},
            response_body=response_body,
        )
        self._by_id[ev.id] = ev
        return ev.id

    def get(self, evidence_id: str) -> Evidence | None:
        return self._by_id.get(evidence_id)

    def link_finding(self, evidence_id: str, finding_node_id: str) -> None:
        ev = self._by_id.get(evidence_id)
        if ev:
            ev.finding_node_id = finding_node_id

    def all(self) -> list[Evidence]:
        return list(self._by_id.values())


# Process-wide store the MITM addon writes into (single orchestrator process).
GLOBAL_STORE = EvidenceStore()
