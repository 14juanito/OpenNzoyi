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


# ── MITRE ATT&CK mapping ─────────────────────────────────────────────────
# Technique IDs most representative of what each tool exercises. Used to tag
# findings and build an ATT&CK coverage view. Names kept short for the UI.
ATTACK_TECHNIQUES: dict[str, list[dict[str, str]]] = {
    "nmap": [{"id": "T1046", "name": "Network Service Discovery"}],
    "rustscan": [{"id": "T1046", "name": "Network Service Discovery"}],
    "httpx": [{"id": "T1595", "name": "Active Scanning"}],
    "subfinder": [{"id": "T1590", "name": "Gather Victim Network Info"}],
    "nuclei": [{"id": "T1595.002", "name": "Vulnerability Scanning"}],
    "ffuf": [{"id": "T1595.003", "name": "Wordlist Scanning"}],
    "sqlmap": [{"id": "T1190", "name": "Exploit Public-Facing Application"}],
    "nikto": [{"id": "T1595.002", "name": "Vulnerability Scanning"}],
    "netexec": [{"id": "T1135", "name": "Network Share Discovery"},
                {"id": "T1110", "name": "Brute Force"}],
    "impacket": [{"id": "T1557", "name": "AiTM / Relay"},
                 {"id": "T1003.006", "name": "DCSync"}],
    "bloodhound": [{"id": "T1482", "name": "Domain Trust Discovery"}],
    "sharphound": [{"id": "T1069.002", "name": "Domain Groups Discovery"}],
    "linpeas": [{"id": "T1082", "name": "System Information Discovery"}],
    "linux-exploit-suggester": [{"id": "T1068", "name": "Privilege Escalation"}],
    "chisel": [{"id": "T1572", "name": "Protocol Tunneling"}],
    "certipy": [{"id": "T1649", "name": "Steal/Forge AD Certificates"}],
    "evil-winrm": [{"id": "T1021.006", "name": "WinRM"}],
    "rubeus": [{"id": "T1558.003", "name": "Kerberoasting"}],
    "mimikatz": [{"id": "T1003.001", "name": "LSASS Memory"}],
    "winpeas": [{"id": "T1082", "name": "System Information Discovery"}],
    "sdn-toolkit": [{"id": "T1599", "name": "Network Boundary Bridging"}],
    "scapy_evasion": [{"id": "T1572", "name": "Protocol Tunneling"},
                      {"id": "T1001", "name": "Data Obfuscation"}],
}


def attack_techniques(tool: str) -> list[dict[str, str]]:
    return ATTACK_TECHNIQUES.get(tool, [])
