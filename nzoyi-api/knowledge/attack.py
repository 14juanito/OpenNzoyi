"""MITRE ATT&CK tactics mapping and coverage aggregation.

Builds on :data:`knowledge.tool_signatures.ATTACK_TECHNIQUES`: maps each
technique to its tactic and aggregates a coverage matrix (tactics x techniques)
from a task's findings and tool executions.
"""

from __future__ import annotations

from typing import Any

from knowledge.tool_signatures import ATTACK_TECHNIQUES, attack_techniques

# Ordered kill-chain tactics (MITRE ATT&CK Enterprise).
TACTICS = [
    "reconnaissance", "discovery", "initial-access", "execution",
    "privilege-escalation", "credential-access", "lateral-movement",
    "command-and-control", "defense-evasion",
]

# Technique ID -> tactic.
TECHNIQUE_TACTIC: dict[str, str] = {
    "T1595": "reconnaissance", "T1595.002": "reconnaissance",
    "T1595.003": "reconnaissance", "T1590": "reconnaissance",
    "T1592": "reconnaissance",
    "T1046": "discovery", "T1135": "discovery", "T1069.002": "discovery",
    "T1482": "discovery", "T1082": "discovery",
    "T1190": "initial-access",
    "T1110": "credential-access", "T1558.003": "credential-access",
    "T1003.001": "credential-access", "T1003.006": "credential-access",
    "T1649": "credential-access", "T1557": "credential-access",
    "T1021.006": "lateral-movement",
    "T1068": "privilege-escalation",
    "T1572": "command-and-control", "T1599": "defense-evasion",
    "T1001": "defense-evasion",
}


def tactic_of(technique_id: str) -> str:
    return TECHNIQUE_TACTIC.get(technique_id, "execution")


def all_techniques() -> list[dict[str, str]]:
    """Flat, de-duplicated list of every known technique with its tactic."""
    seen: dict[str, dict[str, str]] = {}
    for techs in ATTACK_TECHNIQUES.values():
        for t in techs:
            seen[t["id"]] = {"id": t["id"], "name": t["name"],
                             "tactic": tactic_of(t["id"])}
    return sorted(seen.values(), key=lambda t: (TACTICS.index(t["tactic"])
                  if t["tactic"] in TACTICS else 99, t["id"]))


def coverage(findings: list[dict[str, Any]],
             tool_calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Aggregate ATT&CK coverage from findings (+ optional tool executions).

    Returns a per-tactic breakdown with technique hit counts, suitable for a
    tactics x techniques heatmap.
    """
    counts: dict[str, int] = {}

    def bump(tid: str) -> None:
        counts[tid] = counts.get(tid, 0) + 1

    for f in findings:
        for t in f.get("attack", []) or []:
            bump(t["id"])
    for c in tool_calls or []:
        for t in attack_techniques(c.get("tool", "")):
            bump(t["id"])

    by_tactic: dict[str, list[dict[str, Any]]] = {t: [] for t in TACTICS}
    for tech in all_techniques():
        entry = {"id": tech["id"], "name": tech["name"],
                 "count": counts.get(tech["id"], 0)}
        by_tactic.setdefault(tech["tactic"], []).append(entry)

    exercised = sum(1 for v in counts.values() if v > 0)
    return {
        "tactics": TACTICS,
        "by_tactic": by_tactic,
        "techniques_total": len(all_techniques()),
        "techniques_exercised": exercised,
    }
