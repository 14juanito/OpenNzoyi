"""Noise governor — bounds the request rate the RL is allowed to produce.

The RL *optimises* (it may propose a fast, aggressive action); the governor
*bounds* (it never lets the effective rate exceed the task profile's ceiling).
They do not contradict each other: RL proposes, governor clamps.

Profiles (mission brief 7.5):
  quiet      : 2 req/s/host, burst 4,  1 in-flight
  balanced   : 5 req/s/host, burst 10, 2 in-flight
  aggressive : 20 req/s/host, burst 40, 4 in-flight

Jitter is uniform; backoff is exponential on 429/503 and respects Retry-After.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass

GET_CACHE_TTL = {"quiet": 60, "balanced": 30, "aggressive": 10}


@dataclass(frozen=True)
class Profile:
    rate_per_s: float
    burst: int
    in_flight: int


PROFILES: dict[str, Profile] = {
    "quiet": Profile(2.0, 4, 1),
    "balanced": Profile(5.0, 10, 2),
    "aggressive": Profile(20.0, 40, 4),
}


class NoiseGovernor:
    def __init__(self, profile: str = "balanced", jitter: float = 0.1) -> None:
        self.profile = PROFILES.get(profile, PROFILES["balanced"])
        self.profile_name = profile if profile in PROFILES else "balanced"
        self.jitter = jitter
        self._sem = asyncio.Semaphore(self.profile.in_flight)
        self._tokens = float(self.profile.burst)
        self._last = time.monotonic()
        self._backoff_until = 0.0

    @property
    def min_interval_ms(self) -> float:
        """Smallest spacing between requests allowed by the rate ceiling."""
        return 1000.0 / self.profile.rate_per_s

    def clamp_delay(self, proposed_delay_ms: float) -> float:
        """Raise an RL-proposed delay to at least the profile's min interval."""
        return max(float(proposed_delay_ms), self.min_interval_ms)

    def jittered(self, delay_ms: float) -> float:
        if self.jitter <= 0:
            return delay_ms
        return delay_ms * (1.0 + random.uniform(-self.jitter, self.jitter))

    @staticmethod
    def backoff_ms(attempt: int, retry_after_s: float | None = None,
                   base_ms: float = 500.0, cap_ms: float = 30_000.0) -> float:
        if retry_after_s is not None:
            return min(retry_after_s * 1000.0, cap_ms)
        return min(base_ms * (2 ** max(0, attempt)), cap_ms)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(
            self.profile.burst, self._tokens + elapsed * self.profile.rate_per_s
        )

    async def acquire(self, proposed_delay_ms: float = 0.0) -> float:
        """Block until a request may proceed; return the delay actually waited."""
        async with self._sem:
            # Honour an outstanding backoff window.
            now = time.monotonic()
            if now < self._backoff_until:
                await asyncio.sleep(self._backoff_until - now)

            self._refill()
            wait_ms = self.jittered(self.clamp_delay(proposed_delay_ms))
            if self._tokens < 1.0:
                # Not enough tokens: wait for one to accrue.
                need = (1.0 - self._tokens) / self.profile.rate_per_s
                wait_ms = max(wait_ms, need * 1000.0)
            await asyncio.sleep(wait_ms / 1000.0)
            self._refill()
            self._tokens = max(0.0, self._tokens - 1.0)
            return wait_ms

    def note_response(self, status: int, retry_after_s: float | None = None,
                      attempt: int = 0) -> None:
        if status in (429, 503):
            delay = self.backoff_ms(attempt, retry_after_s) / 1000.0
            self._backoff_until = time.monotonic() + delay
