"""Budget gate — global token/turn ceiling with forced wrap-up.

Decremented at each LLM call / worker turn. When the remaining budget falls
below the estimated cost of one more worker, the task is told to wrap up instead
of starting new work. The per-worker estimate defaults to 50k tokens / 10 turns
and is refined with the running average of completed workers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_TOKENS_PER_WORKER = 50_000
DEFAULT_TURNS_PER_WORKER = 10


@dataclass
class Budget:
    budget_tokens: int | None = None
    budget_turns: int | None = None
    tokens_used: int = 0
    turns_used: int = 0
    _worker_tokens: list[int] = field(default_factory=list)
    _worker_turns: list[int] = field(default_factory=list)

    def charge(self, tokens: int = 0, turns: int = 0) -> None:
        self.tokens_used += max(0, tokens)
        self.turns_used += max(0, turns)

    def record_worker(self, tokens: int, turns: int) -> None:
        if tokens > 0:
            self._worker_tokens.append(tokens)
        if turns > 0:
            self._worker_turns.append(turns)

    def _est_tokens(self) -> int:
        if self._worker_tokens:
            return int(sum(self._worker_tokens) / len(self._worker_tokens))
        return DEFAULT_TOKENS_PER_WORKER

    def _est_turns(self) -> int:
        if self._worker_turns:
            return int(sum(self._worker_turns) / len(self._worker_turns))
        return DEFAULT_TURNS_PER_WORKER

    def tokens_remaining(self) -> int | None:
        return None if self.budget_tokens is None else self.budget_tokens - self.tokens_used

    def turns_remaining(self) -> int | None:
        return None if self.budget_turns is None else self.budget_turns - self.turns_used

    def exhausted(self) -> bool:
        tr = self.tokens_remaining()
        ur = self.turns_remaining()
        return (tr is not None and tr <= 0) or (ur is not None and ur <= 0)

    def should_wrap_up(self) -> bool:
        """True when there isn't enough budget left for one more worker."""
        tr = self.tokens_remaining()
        ur = self.turns_remaining()
        if tr is not None and tr < self._est_tokens():
            return True
        if ur is not None and ur < self._est_turns():
            return True
        return False
