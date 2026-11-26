"""Main agent — human-in-the-loop conversational layer.

The operator talks to the "main agent" to get a situational analysis of a task
and to inject hints / high-priority intents that steer the Planner. This layer
is strategic (it may use an LLM); it NEVER touches the RL evasion loop.

Default behaviour is a deterministic situational analysis derived from the
task's exploration graph (skill principle #2: no hard dependency on a network
LLM). If an LLM backend is wired in later, it can replace :func:`analyze` while
keeping this deterministic path as the guaranteed fallback.
"""

from __future__ import annotations

from typing import Any

_PHASE_ORDER = ["recon", "vuln", "ad_enum", "linux", "lateral", "post"]
_NEXT_SUGGESTION = {
    "recon": "lancer l'analyse de vulnérabilités (nuclei/ffuf) sur les services exposés",
    "vuln": "pivoter vers l'énumération AD si un port SMB/445 est ouvert, sinon la priv-esc Linux",
    "ad_enum": "tenter le mouvement latéral (impacket/evil-winrm) avec les comptes découverts",
    "linux": "consolider l'accès et lancer la post-exploitation",
    "lateral": "post-exploitation : extraction d'identifiants et persistance (actions gatées)",
    "post": "rédiger le rapport : toutes les phases offensives ont été parcourues",
}


def summarize_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    facts = [n for n in nodes if n["type"] == "fact"]
    findings = [n for n in nodes if n["type"] == "finding"]
    phases_done = sorted({f["content"].get("kind") for f in facts if f["content"].get("kind")})
    sev: dict[str, int] = {}
    for f in findings:
        s = f["content"].get("severity", "info")
        sev[s] = sev.get(s, 0) + 1
    last_phase = phases_done[-1] if phases_done else None
    nxt = None
    if last_phase:
        idx = _PHASE_ORDER.index(last_phase) if last_phase in _PHASE_ORDER else -1
        nxt = _PHASE_ORDER[idx + 1] if 0 <= idx < len(_PHASE_ORDER) - 1 else "post"
    return {
        "phases_done": phases_done,
        "facts": len(facts),
        "findings": len(findings),
        "severity": sev,
        "next_phase": nxt,
    }


def analyze(task: dict[str, Any], graph: dict[str, Any], user_msg: str) -> str:
    """Deterministic situational analysis of a task, in reply to ``user_msg``."""
    s = summarize_graph(graph)
    target = task.get("target", "?")
    lines: list[str] = []

    if not s["phases_done"]:
        lines.append(
            f"Aucune donnée d'exploration pour {target} pour l'instant. "
            "Lance ou relance la tâche pour démarrer la reconnaissance."
        )
    else:
        done = ", ".join(s["phases_done"])
        lines.append(
            f"État de {target} : phases couvertes = {done} · "
            f"{s['facts']} fait(s), {s['findings']} finding(s)."
        )
        if s["severity"]:
            sev = ", ".join(f"{k}:{v}" for k, v in sorted(s["severity"].items()))
            lines.append(f"Répartition des findings par sévérité : {sev}.")
        if s["next_phase"]:
            tip = _NEXT_SUGGESTION.get(s["next_phase"], "")
            lines.append(f"Prochaine étape recommandée — {s['next_phase']} : {tip}.")

    # Light intent detection to guide the operator toward hint injection.
    low = user_msg.lower()
    if any(w in low for w in ("hint", "prioris", "focus", "oriente", "cible")):
        lines.append(
            "Pour orienter l'agent, injecte un hint (bouton « Injecter un hint ») : "
            "il crée un nœud prioritaire que le Planner consommera en premier."
        )
    elif any(w in low for w in ("résum", "summary", "chain", "kill", "rapport")):
        lines.append(
            "Chaîne d'attaque reconstituée depuis le graphe d'exploration "
            "(arêtes spawns → yields → proves) — voir l'onglet Report de la tâche."
        )
    return "\n".join(lines)
