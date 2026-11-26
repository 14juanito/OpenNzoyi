"""NZOYI RL microservice (nzoyi-core).

FastAPI wrapper around the unmodified tabular Q-Learning core. The orchestrator
(nzoyi-api) consults this service for the next evasion action and feeds back the
observed reward. No LLM is involved anywhere in this service — that is a hard
architectural constraint of NZOYI.

Endpoints
---------
POST /evasion/next_action   {task_id, state, phase}
POST /evasion/update        {task_id, state, action_hash, reward, next_state}
GET  /evasion/policy/{task_id}?phase=...
POST /evasion/reset/{task_id}
GET  /health
"""

from __future__ import annotations

import os
import random
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from evasion.q_learner import EvasionAction, EvasionQLearner
from evasion.state import (
    STATE_FIELDS,
    STATE_SPACE_SIZE,
    StateError,
    phase_of,
    state_hash,
    validate_state,
)
from evasion.action import (
    ActionError,
    action_space_size,
    decode_action_hash,
    enumerate_action_hashes,
    phase_actions,
)
from evasion.policy_store import (
    MemoryPolicyStore,
    get_policy_store,
    make_q_key,
)

# ── Hyperparameters (env-configurable, convention NZOYI_RL_*) ────────────────
_ALPHA = float(os.environ.get("NZOYI_RL_ALPHA", "0.1"))
_GAMMA = float(os.environ.get("NZOYI_RL_GAMMA", "0.9"))
_EPSILON = float(os.environ.get("NZOYI_RL_EPSILON", "0.2"))
_EPSILON_DECAY = float(os.environ.get("NZOYI_RL_EPSILON_DECAY", "0.995"))
_EPSILON_MIN = float(os.environ.get("NZOYI_RL_EPSILON_MIN", "0.05"))
_SEED_ENV = os.environ.get("NZOYI_RL_SEED")

_STORE = get_policy_store()


def _rng() -> random.Random:
    """Deterministic RNG when NZOYI_RL_SEED is set, else entropy-seeded."""
    return random.Random(int(_SEED_ENV)) if _SEED_ENV else random.Random()


class _KeyState:
    """Minimal state carrier exposing ``as_key()`` for the Q-Learner.

    Lets the unmodified EvasionQLearner key its table by the rich state hash
    without knowing anything about the state representation.
    """

    __slots__ = ("_hash",)

    def __init__(self, h: str) -> None:
        self._hash = h

    def as_key(self) -> str:
        return self._hash


# ── Request / response schemas ───────────────────────────────────────────────
class NextActionRequest(BaseModel):
    task_id: str
    state: dict[str, str]
    phase: str


class NextActionResponse(BaseModel):
    tool: str
    timing: str
    delay: int
    frag: bool
    action_hash: str
    state_hash: str
    explored: bool = Field(
        description="True if epsilon-greedy picked a random (exploratory) action"
    )


class UpdateRequest(BaseModel):
    task_id: str
    state: dict[str, str]
    action_hash: str
    reward: float
    next_state: dict[str, str]


class UpdateResponse(BaseModel):
    q_key: str
    q_value: float
    phase: str


app = FastAPI(title="NZOYI RL core", version="1.0.0")


@app.get("/health")
def health() -> dict[str, Any]:
    backend = "memory" if isinstance(_STORE, MemoryPolicyStore) else "postgres"
    return {
        "status": "ok",
        "service": "nzoyi-core",
        "policy_backend": backend,
        "state_space_size": STATE_SPACE_SIZE,
        "phases": list(STATE_FIELDS["phase"]),
        "llm_in_loop": False,
    }


@app.post("/evasion/next_action", response_model=NextActionResponse)
def next_action(req: NextActionRequest) -> NextActionResponse:
    try:
        norm = validate_state(req.state)
    except StateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if norm["phase"] != req.phase:
        raise HTTPException(
            status_code=422,
            detail=f"incohérence phase: state.phase={norm['phase']} != {req.phase}",
        )
    try:
        actions = phase_actions(req.phase)
    except ActionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    learner = EvasionQLearner(
        alpha=_ALPHA,
        gamma=_GAMMA,
        epsilon=_EPSILON,
        epsilon_decay=_EPSILON_DECAY,
        epsilon_min=_EPSILON_MIN,
        actions=actions,
    )
    learner.q_table = _STORE.load_phase(req.task_id, req.phase)

    sh = state_hash(norm)
    key_state = _KeyState(sh)

    # Greedy reference BEFORE sampling: lets us report whether the epsilon-greedy
    # draw explored, without reimplementing or modifying the learner.
    greedy = max(actions, key=lambda a: learner._q(key_state, a.name))
    chosen: EvasionAction = learner.choose_action(key_state, _rng())
    explored = chosen.name != greedy.name

    decoded = decode_action_hash(chosen.name)
    return NextActionResponse(
        tool=str(decoded["tool"]),
        timing=str(decoded["timing"]),
        delay=int(decoded["delay"]),
        frag=bool(decoded["frag"]),
        action_hash=chosen.name,
        state_hash=sh,
        explored=explored,
    )


@app.post("/evasion/update", response_model=UpdateResponse)
def update(req: UpdateRequest) -> UpdateResponse:
    try:
        norm_state = validate_state(req.state)
        norm_next = validate_state(req.next_state)
    except StateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    state_phase = norm_state["phase"]
    next_phase = norm_next["phase"]

    # Validate the acted action belongs to the state's phase action space.
    if req.action_hash not in enumerate_action_hashes(state_phase):
        raise HTTPException(
            status_code=422,
            detail=f"action '{req.action_hash}' hors espace de la phase '{state_phase}'",
        )

    # Bootstrap target max() is taken over the NEXT state's phase actions.
    learner = EvasionQLearner(
        alpha=_ALPHA,
        gamma=_GAMMA,
        epsilon=_EPSILON,
        epsilon_decay=_EPSILON_DECAY,
        epsilon_min=_EPSILON_MIN,
        actions=phase_actions(next_phase),
    )
    # Load the whole task so the cross-phase bootstrap sees next-state values.
    learner.q_table = _STORE.load_task(req.task_id)

    state_obj = _KeyState(state_hash(norm_state))
    next_obj = _KeyState(state_hash(norm_next))
    action = EvasionAction(name=req.action_hash)

    learner.update(state_obj, action, float(req.reward), next_obj)

    q_key = make_q_key(state_hash(norm_state), req.action_hash)
    q_value = learner.q_table[q_key]
    _STORE.upsert(req.task_id, state_phase, {q_key: q_value})

    return UpdateResponse(q_key=q_key, q_value=q_value, phase=state_phase)


@app.get("/evasion/policy/{task_id}")
def policy(task_id: str, phase: str | None = None) -> dict[str, Any]:
    if phase is not None and phase not in STATE_FIELDS["phase"]:
        raise HTTPException(status_code=422, detail=f"phase inconnue: '{phase}'")
    summary = _STORE.summary(task_id, phase)
    out: dict[str, Any] = {"task_id": task_id, "phase": phase, "summary": summary}
    if phase is not None:
        out["action_space_size"] = action_space_size(phase)
    return out


@app.post("/evasion/reset/{task_id}")
def reset(task_id: str) -> dict[str, Any]:
    removed = _STORE.reset(task_id)
    return {"task_id": task_id, "removed_cells": removed}
