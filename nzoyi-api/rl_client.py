"""Client to the nzoyi-core RL microservice.

Two transports, same interface (skill principle #2: deterministic fallback, no
hard network dependency):

* HTTP  — when ``NZOYI_CORE_URL`` is set, talk to the running microservice.
* in-process — otherwise, import the microservice's own handlers directly
  (single source of truth: the exact same evasion logic, no duplication).

The dispatcher calls :meth:`next_action` before every offensive step and
:meth:`update` after the EvaluationAgent computes the reward.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_CORE_DIR = Path(__file__).resolve().parent.parent / "nzoyi-core"


class RLClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.environ.get("NZOYI_CORE_URL")
        self._api = None  # lazily imported in-process handler module

    # ── transport selection ──────────────────────────────────────────────
    def _inproc(self):
        if self._api is None:
            if str(_CORE_DIR) not in sys.path:
                sys.path.insert(0, str(_CORE_DIR))
            import api  # nzoyi-core/api.py

            self._api = api
        return self._api

    # ── API ──────────────────────────────────────────────────────────────
    def next_action(
        self, task_id: str, state: dict[str, str], phase: str
    ) -> dict[str, Any]:
        if self.base_url:
            import httpx

            r = httpx.post(
                f"{self.base_url}/evasion/next_action",
                json={"task_id": task_id, "state": state, "phase": phase},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        api = self._inproc()
        resp = api.next_action(
            api.NextActionRequest(task_id=task_id, state=state, phase=phase)
        )
        return resp.model_dump()

    def update(
        self,
        task_id: str,
        state: dict[str, str],
        action_hash: str,
        reward: float,
        next_state: dict[str, str],
    ) -> dict[str, Any]:
        if self.base_url:
            import httpx

            r = httpx.post(
                f"{self.base_url}/evasion/update",
                json={
                    "task_id": task_id,
                    "state": state,
                    "action_hash": action_hash,
                    "reward": reward,
                    "next_state": next_state,
                },
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        api = self._inproc()
        resp = api.update(
            api.UpdateRequest(
                task_id=task_id,
                state=state,
                action_hash=action_hash,
                reward=reward,
                next_state=next_state,
            )
        )
        return resp.model_dump()
