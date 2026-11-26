"""Per-phase action space for the NZOYI evasion RL microservice.

An action bundles the tactical knobs the auditor can turn for one offensive
step: which tool to launch, the scan-timing template, an inter-request delay and
whether to fragment. The tool set is phase-dependent; timing/delay/fragment are
shared.

As with :mod:`evasion.state`, the Q-Learning core never inspects an action's
structure — it only reads ``action.name`` (the :func:`action_hash`). The
historical delta-based :class:`nzoyi.rl.qlearning.EvasionAction` is reused
verbatim as the carrier type: we instantiate it with ``name=<action_hash>`` and
ignore its delta fields, so ``q_learner.py`` stays unmodified.
"""

from __future__ import annotations

from itertools import product

# Reuse the untouched carrier dataclass from the moved Q-Learning module.
from evasion.q_learner import EvasionAction

TOOLS_BY_PHASE: dict[str, list[str]] = {
    "recon": ["nmap", "rustscan", "httpx", "subfinder"],
    "vuln": ["nuclei", "ffuf", "sqlmap", "nikto"],
    "ad_enum": ["netexec", "impacket", "sharphound", "bloodhound"],
    "linux": ["linpeas", "linux-exploit-suggester"],
    "lateral": ["impacket", "evil-winrm", "chisel"],
    "evasion": ["sdn-toolkit", "iodine", "scapy_frag"],
    "post": ["mimikatz", "winpeas", "rubeus", "certipy"],
}

TIMINGS: list[str] = ["T1", "T2", "T3", "T4"]
DELAYS: list[int] = [0, 250, 500, 1000]
FRAGS: list[bool] = [False, True]

# Field delimiter inside an action hash. MUST NOT be ':' (see state.py).
_SEP = "."


class ActionError(ValueError):
    """Raised for an unknown phase or an action outside the declared space."""


def action_hash(tool: str, timing: str, delay: int, frag: bool) -> str:
    """Canonical, reversible hash of an action tuple."""
    return _SEP.join([tool, timing, str(int(delay)), str(int(bool(frag)))])


def decode_action_hash(h: str) -> dict[str, object]:
    """Inverse of :func:`action_hash`."""
    parts = h.split(_SEP)
    if len(parts) != 4:
        raise ActionError(f"action_hash malformé: '{h}'")
    tool, timing, delay, frag = parts
    return {
        "tool": tool,
        "timing": timing,
        "delay": int(delay),
        "frag": bool(int(frag)),
    }


def enumerate_action_hashes(phase: str) -> list[str]:
    """All action hashes available in ``phase`` (|tools| x 4 x 4 x 2)."""
    if phase not in TOOLS_BY_PHASE:
        raise ActionError(
            f"phase inconnue: '{phase}'. Connu: {sorted(TOOLS_BY_PHASE)}."
        )
    hashes: list[str] = []
    for tool, timing, delay, frag in product(
        TOOLS_BY_PHASE[phase], TIMINGS, DELAYS, FRAGS
    ):
        hashes.append(action_hash(tool, timing, delay, frag))
    return hashes


def phase_actions(phase: str) -> tuple[EvasionAction, ...]:
    """Build the carrier action tuple for a phase (names = action hashes).

    This is what :class:`~evasion.q_learner.EvasionQLearner` receives as its
    ``actions=`` argument. The delta fields stay at their defaults and are never
    used by the operational policy; only ``.name`` (the action hash) matters.
    """
    return tuple(EvasionAction(name=h) for h in enumerate_action_hashes(phase))


def action_space_size(phase: str) -> int:
    return len(TOOLS_BY_PHASE[phase]) * len(TIMINGS) * len(DELAYS) * len(FRAGS)
