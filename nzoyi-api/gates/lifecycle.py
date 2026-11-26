"""Task lifecycle — hard kill, persistence rollback, per-intent timeout.

``DELETE /api/tasks/{id}`` triggers :meth:`TaskLifecycle.kill`: it cancels every
in-flight worker and runs the registered rollback callbacks in reverse order
(services, crons, SSH keys, run-keys installed during the run). Each intent also
runs under a timeout so a worker that never concludes is killed.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger("nzoyi.lifecycle")


@dataclass
class Rollback:
    description: str
    undo: Callable[[], Awaitable[None]] | Callable[[], None]


@dataclass
class TaskLifecycle:
    task_id: str
    intent_timeout_s: int = 600
    _workers: set[asyncio.Task] = field(default_factory=set)
    _rollbacks: list[Rollback] = field(default_factory=list)
    killed: bool = False

    def register_persistence(self, description: str, undo) -> None:
        """Record an installed persistence so kill() can roll it back."""
        self._rollbacks.append(Rollback(description, undo))

    def track(self, coro: Awaitable) -> asyncio.Task:
        task = asyncio.ensure_future(coro)
        self._workers.add(task)
        task.add_done_callback(self._workers.discard)
        return task

    async def run_intent(self, coro: Awaitable):
        """Run an intent under the per-intent timeout; kill it if it hangs."""
        return await asyncio.wait_for(coro, timeout=self.intent_timeout_s)

    async def kill(self) -> dict[str, int]:
        """Cancel workers and roll back persistences (reverse order)."""
        self.killed = True
        cancelled = 0
        for task in list(self._workers):
            if not task.done():
                task.cancel()
                cancelled += 1
        rolled = 0
        for rb in reversed(self._rollbacks):
            try:
                res = rb.undo()
                if asyncio.iscoroutine(res):
                    await res
                rolled += 1
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                logger.warning("rollback '%s' a échoué: %s", rb.description, exc)
        self._rollbacks.clear()
        return {"workers_cancelled": cancelled, "rollbacks_done": rolled}
