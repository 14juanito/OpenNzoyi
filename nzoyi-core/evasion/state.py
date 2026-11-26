"""Explicit state space for the NZOYI evasion RL microservice.

The historical :class:`nzoyi.rl.qlearning.EvasionState` (timing/delay/fragment,
72 states) is preserved untouched inside ``q_learner.py`` for the offline
research baseline. This module defines the *richer* operational state space the
autonomous auditor reasons over, without modifying the Q-Learning algorithm:
the learner only ever sees the opaque, hashable key produced by
:func:`state_hash`, so the pure tabular update logic in ``q_learner.py`` stays
byte-identical.

State dimensions (section 3 of the mission brief)::

    target_os         x2
    open_ports_bucket x3
    privilege_level   x4
    alert_count_5min  x3
    sdn_flow_blocks   x3
    phase             x7
    ------------------------
    total = 2*3*4*3*3*7 = 1512 states
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable

# Ordered so the hash is stable across processes. DO NOT reorder without a
# migration: existing q_tables rows are keyed by the string these produce.
STATE_FIELDS: dict[str, list[str]] = {
    "target_os": ["linux", "windows"],
    "open_ports_bucket": ["0-3", "4-10", "11+"],
    "privilege_level": ["user", "sudo", "admin", "system"],
    "alert_count_5min": ["0", "1-3", "4+"],
    "sdn_flow_blocks": ["0", "1-2", "3+"],
    "phase": ["recon", "vuln", "ad_enum", "linux", "lateral", "evasion", "post"],
}

STATE_SPACE_SIZE = 1
for _vals in STATE_FIELDS.values():
    STATE_SPACE_SIZE *= len(_vals)  # -> 1512

# Field delimiter inside a state hash. MUST NOT be ':' because q_learner.py
# composes Q-table keys as f"{state.as_key()}:{action.name}" and splits on ':'.
_SEP = "."


class StateError(ValueError):
    """Raised when a state dict is malformed or out of the declared space."""


def bucket_open_ports(n: int) -> str:
    """Map an open-port count to its declared bucket label."""
    if n <= 3:
        return "0-3"
    if n <= 10:
        return "4-10"
    return "11+"


def bucket_alerts(n: int) -> str:
    """Map a 5-minute alert count to its declared bucket label."""
    if n <= 0:
        return "0"
    if n <= 3:
        return "1-3"
    return "4+"


def bucket_sdn_blocks(n: int) -> str:
    """Map an SDN flow-block count to its declared bucket label."""
    if n <= 0:
        return "0"
    if n <= 2:
        return "1-2"
    return "3+"


@dataclass(frozen=True)
class EvasionStateV2:
    """A point in the explicit operational state space.

    The learner never inspects the fields; it only calls :meth:`as_key`, which
    returns the canonical, reversible :func:`state_hash`. This keeps the
    Q-Learning core agnostic of the state representation.
    """

    target_os: str
    open_ports_bucket: str
    privilege_level: str
    alert_count_5min: str
    sdn_flow_blocks: str
    phase: str

    def as_key(self) -> Hashable:  # consumed verbatim by q_learner.py
        return state_hash(self.as_dict())

    def as_dict(self) -> dict[str, str]:
        return {
            "target_os": self.target_os,
            "open_ports_bucket": self.open_ports_bucket,
            "privilege_level": self.privilege_level,
            "alert_count_5min": self.alert_count_5min,
            "sdn_flow_blocks": self.sdn_flow_blocks,
            "phase": self.phase,
        }


def validate_state(state: dict[str, str]) -> dict[str, str]:
    """Validate a raw state dict against :data:`STATE_FIELDS`.

    Returns the normalized dict (same values, canonical field order).

    Raises:
        StateError: on any missing field or value outside the declared space.
    """
    normalized: dict[str, str] = {}
    for field, allowed in STATE_FIELDS.items():
        if field not in state:
            raise StateError(f"champ d'état manquant: '{field}'")
        value = str(state[field])
        if value not in allowed:
            raise StateError(
                f"valeur '{value}' hors domaine pour '{field}'. "
                f"Attendu l'un de {allowed}."
            )
        normalized[field] = value
    return normalized


def state_hash(state: dict[str, str]) -> str:
    """Canonical, reversible hash of a validated state.

    The hash is the ordinal index of each field value joined by ``.`` — compact,
    stable, collision-free within the declared space, and decodable via
    :func:`decode_state_hash`.
    """
    normalized = validate_state(state)
    parts = [
        str(STATE_FIELDS[field].index(normalized[field]))
        for field in STATE_FIELDS
    ]
    return _SEP.join(parts)


def decode_state_hash(h: str) -> dict[str, str]:
    """Inverse of :func:`state_hash`."""
    parts = h.split(_SEP)
    fields = list(STATE_FIELDS)
    if len(parts) != len(fields):
        raise StateError(f"state_hash malformé: '{h}'")
    decoded: dict[str, str] = {}
    for field, raw in zip(fields, parts):
        try:
            decoded[field] = STATE_FIELDS[field][int(raw)]
        except (ValueError, IndexError) as exc:
            raise StateError(f"index invalide dans state_hash '{h}'") from exc
    return decoded


def phase_of(state: dict[str, str]) -> str:
    """Extract the phase from a (validated) state dict."""
    return validate_state(state)["phase"]
