"""NZOYI evasion RL core.

The Q-Learning algorithm (``q_learner.py``) is a byte-identical copy of
``nzoyi/rl/qlearning.py`` and is NEVER modified here. No module in this package
imports any language-model backend — a hard architectural constraint, enforced
by ``scripts/verify.sh`` (the evasion package must contain zero references to
the orchestrator's language-model layer or any provider SDK).
"""

from evasion.q_learner import EvasionAction, EvasionQLearner, EvasionState
from evasion.state import (
    STATE_FIELDS,
    STATE_SPACE_SIZE,
    EvasionStateV2,
    decode_state_hash,
    state_hash,
    validate_state,
)
from evasion.action import (
    TOOLS_BY_PHASE,
    action_hash,
    decode_action_hash,
    enumerate_action_hashes,
    phase_actions,
)
from evasion.policy_store import PolicyStore, get_policy_store

__all__ = [
    "EvasionAction",
    "EvasionQLearner",
    "EvasionState",
    "EvasionStateV2",
    "STATE_FIELDS",
    "STATE_SPACE_SIZE",
    "state_hash",
    "decode_state_hash",
    "validate_state",
    "TOOLS_BY_PHASE",
    "action_hash",
    "decode_action_hash",
    "enumerate_action_hashes",
    "phase_actions",
    "PolicyStore",
    "get_policy_store",
]
