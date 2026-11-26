"""Global interception-rules store (editable from the UI).

Mirrors the ``approval_rules`` table. The dispatcher's interception gate reads
these rules so an operator can, at runtime, force-approve / deny / require-human
for commands matching a string, regex or argv prefix.
"""

from __future__ import annotations

import itertools
import threading
from typing import Any

from gates.interception_gate import ApprovalRule

_VALID_TYPES = {"string", "regex", "argv_prefix"}
_VALID_ACTIONS = {"approve", "deny", "require_human"}


class RulesStore:
    def __init__(self) -> None:
        self._rules: dict[int, dict[str, Any]] = {}
        self._seq = itertools.count(1)
        self._lock = threading.RLock()

    def add(self, rule_type: str, pattern: Any, action: str) -> dict[str, Any]:
        if rule_type not in _VALID_TYPES:
            raise ValueError(f"type de règle invalide: {rule_type}")
        if action not in _VALID_ACTIONS:
            raise ValueError(f"action invalide: {action}")
        if rule_type == "argv_prefix" and isinstance(pattern, str):
            pattern = pattern.split()
        with self._lock:
            rid = next(self._seq)
            self._rules[rid] = {"id": rid, "rule_type": rule_type,
                                "pattern": pattern, "action": action}
            return self._rules[rid]

    def delete(self, rid: int) -> bool:
        with self._lock:
            return self._rules.pop(rid, None) is not None

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._rules.values())

    def as_approval_rules(self) -> list[ApprovalRule]:
        with self._lock:
            return [ApprovalRule(r["rule_type"], r["pattern"], r["action"])
                    for r in self._rules.values()]


GLOBAL_RULES = RulesStore()
