"""Tool detection signatures — a PRIOR for the RL, not a policy.

Each entry estimates how noisy a tool is (Suricata SIDs / Sysmon event IDs it
typically triggers, a prior detection probability) and known evasion tips. After
each execution the EvaluationAgent compares the predicted ``detection_probability``
with the observed ``alerts_generated`` and nudges the estimate — so these numbers
are seeds, never fixed truth.
"""

from __future__ import annotations

from typing import Any

TOOL_SIGNATURES: dict[str, dict[str, Any]] = {
    "nmap": {
        "suricata_sids": ["2010935", "2010936"],
        "sysmon_events": [],
        "detection_probability": 0.85,
        "evasion_tips": ["-T2", "--max-rate 10", "-f"],
    },
    "nuclei": {
        "suricata_sids": ["2024897"],
        "sysmon_events": [],
        "detection_probability": 0.60,
        "evasion_tips": ["-H 'User-Agent: Mozilla/5.0'", "-rate-limit 5"],
    },
    "psexec": {
        "suricata_sids": [],
        "sysmon_events": ["1", "7045"],
        "detection_probability": 0.95,
        "evasion_tips": ["préférer wmiexec", "espacer de 60s"],
    },
    "wmiexec": {
        "suricata_sids": [],
        "sysmon_events": ["1", "4688"],
        "detection_probability": 0.40,
        "evasion_tips": ["-silent", "éviter les commandes longues"],
    },
    "linpeas": {
        "suricata_sids": [],
        "sysmon_events": [],
        "detection_probability": 0.10,
        "evasion_tips": ["exécuter en mémoire si possible"],
    },
}


def signature(tool: str) -> dict[str, Any]:
    """Return the signature for ``tool`` (empty prior if unknown)."""
    return TOOL_SIGNATURES.get(
        tool,
        {"suricata_sids": [], "sysmon_events": [],
         "detection_probability": 0.5, "evasion_tips": []},
    )


def prior_detection(tool: str) -> float:
    return float(signature(tool)["detection_probability"])
