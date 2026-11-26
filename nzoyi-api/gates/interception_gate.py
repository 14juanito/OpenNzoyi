"""Interception gate — gates destructive / high-signal actions.

Modes:
  * ``autonomous`` (default)  : destructive actions proceed; decisions logged.
  * ``semi``                  : destructive actions need a human approval.

Rule types (``approval_rules`` table):
  * ``string``      : exact match on the full command string.
  * ``regex``       : regex search on the full command string.
  * ``argv_prefix`` : JSON array of 1–8 tokens; matches ONLY a simple command
                      whose parsed argv prefix equals the pattern exactly. A
                      command containing a pipe, list, redirection, command
                      substitution or a wrapper does NOT match (defence against
                      prefix-spoofing).

Default destructive capabilities always require interception in ``semi`` mode:
dcsync, lsass_dump, exploit_kernel, ssh_key_inject, service_create,
certipy_exploit, mimikatz, persistence_*.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import Any

from gates.scope_gate import GateDecision

_DANGEROUS_RE = re.compile(r"[|&;<>`$()]|\$\(|\n")

DEFAULT_DESTRUCTIVE = {
    "dcsync", "lsass_dump", "exploit_kernel", "ssh_key_inject",
    "service_create", "certipy_exploit", "mimikatz",
}


def _is_persistence(token: str) -> bool:
    return token.startswith("persistence_")


@dataclass
class ApprovalRule:
    rule_type: str  # string | regex | argv_prefix
    pattern: Any    # str, or list[str] for argv_prefix
    action: str     # approve | deny | require_human


def _argv_prefix_matches(command: list[str] | str, pattern: list[str]) -> bool:
    if not pattern or len(pattern) > 8:
        return False
    if isinstance(command, str):
        # A simple command only: reject anything with shell metacharacters.
        if _DANGEROUS_RE.search(command):
            return False
        try:
            argv = shlex.split(command)
        except ValueError:
            return False
    else:
        argv = list(command)
    return argv[: len(pattern)] == list(pattern)


def _rule_matches(rule: ApprovalRule, command: list[str]) -> bool:
    cmd_str = " ".join(command)
    if rule.rule_type == "string":
        return cmd_str == rule.pattern
    if rule.rule_type == "regex":
        try:
            return re.search(rule.pattern, cmd_str) is not None
        except re.error:
            return False
    if rule.rule_type == "argv_prefix":
        return _argv_prefix_matches(command, rule.pattern)
    return False


class InterceptionGate:
    def __init__(
        self,
        rules: list[ApprovalRule] | None = None,
        mode: str = "autonomous",
    ) -> None:
        self.rules = rules or []
        self.mode = mode

    def _is_destructive(self, tool_name: str, requires_interception: bool) -> bool:
        return (
            requires_interception
            or tool_name in DEFAULT_DESTRUCTIVE
            or _is_persistence(tool_name)
        )

    def check(
        self,
        tool_name: str,
        command: list[str],
        requires_interception: bool = False,
    ) -> GateDecision:
        # Explicit rules win (deny > require_human > approve), by first match.
        for rule in self.rules:
            if _rule_matches(rule, command):
                allowed = rule.action == "approve"
                return GateDecision(
                    allowed, "interception",
                    f"règle {rule.rule_type} → {rule.action}",
                    {"tool": tool_name, "decided_by": "rule", "action": rule.action},
                ).log()

        if self._is_destructive(tool_name, requires_interception):
            if self.mode == "semi":
                return GateDecision(
                    False, "interception",
                    "action destructrice — approbation humaine requise",
                    {"tool": tool_name, "decided_by": "system",
                     "action": "require_human"},
                ).log()
            return GateDecision(
                True, "interception", "mode autonome — action autorisée",
                {"tool": tool_name, "decided_by": "system", "action": "approve"},
            ).log()

        return GateDecision(
            True, "interception", "non destructif", {"tool": tool_name}
        ).log()
