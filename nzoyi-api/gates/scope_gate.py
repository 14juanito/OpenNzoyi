"""Scope gate — refuses any intent whose target is outside the declared scope.

Two conditions (mission brief 7.1):
  1. target ∈ task.scope  (a declared CIDR or domain)
  2. target ∈ assets      (discovered by a tool — not an invented IP), unless it
     is the declared root target itself.

Every decision is logged as structured JSON so refusals are auditable.
"""

from __future__ import annotations

import ipaddress
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("nzoyi.gates.scope")


@dataclass
class GateDecision:
    allowed: bool
    gate: str
    reason: str = ""
    detail: dict[str, Any] | None = None

    def log(self) -> "GateDecision":
        logger.info(
            json.dumps({
                "gate": self.gate,
                "decision": "allow" if self.allowed else "deny",
                "reason": self.reason,
                **(self.detail or {}),
            })
        )
        return self


def _in_cidr_or_domain(host: str, scope: dict[str, Any]) -> bool:
    for cidr in scope.get("cidrs", []):
        try:
            if ipaddress.ip_address(host) in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    for dom in scope.get("domains", []):
        if host == dom or host.endswith("." + dom):
            return True
    return False


class ScopeGate:
    def __init__(
        self,
        scope: dict[str, Any],
        known_assets: Callable[[], set[str]],
        root_target: str | None = None,
    ) -> None:
        self.scope = scope
        self.known_assets = known_assets
        self.root_target = root_target

    def check(self, host: str) -> GateDecision:
        if not _in_cidr_or_domain(host, self.scope):
            return GateDecision(
                False, "scope", f"hors périmètre déclaré: {host}",
                {"target": host}
            ).log()
        # Anti-invention: must be the root target or a discovered asset.
        if host != self.root_target and host not in self.known_assets():
            return GateDecision(
                False, "scope", f"cible non découverte (inventée ?): {host}",
                {"target": host}
            ).log()
        return GateDecision(True, "scope", "in-scope", {"target": host}).log()
