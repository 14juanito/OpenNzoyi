"""Async subprocess runner shared by every tool wrapper.

Degrades gracefully: if the binary is absent the call returns a ``skipped``
result instead of raising, so the orchestration loop stays runnable on a host
that does not have the full offensive toolchain installed (dev / CI).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from dataclasses import dataclass


@dataclass
class ProcResult:
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    found: bool  # whether the binary existed and ran


async def run_subprocess(
    cmd: list[str],
    timeout: int = 300,
    proxy: str | None = None,
    env_extra: dict[str, str] | None = None,
) -> ProcResult:
    """Run ``cmd`` asynchronously with an optional HTTP(S) proxy.

    ``proxy`` is injected via ``HTTP_PROXY``/``HTTPS_PROXY`` so HTTP-speaking
    tools route through the evidence MITM proxy (Phase 4). Binaries that accept
    a proxy flag set it themselves in their wrapper.
    """
    binary = cmd[0]
    if shutil.which(binary) is None:
        return ProcResult(127, "", f"binary '{binary}' introuvable", 0, found=False)

    env = os.environ.copy()
    if proxy:
        env["HTTP_PROXY"] = proxy
        env["HTTPS_PROXY"] = proxy
        env["http_proxy"] = proxy
        env["https_proxy"] = proxy
    if env_extra:
        env.update(env_extra)

    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            dur = int((time.monotonic() - start) * 1000)
            return ProcResult(124, "", f"timeout après {timeout}s", dur, found=True)
    except OSError as exc:
        dur = int((time.monotonic() - start) * 1000)
        return ProcResult(126, "", f"échec d'exécution: {exc}", dur, found=True)

    dur = int((time.monotonic() - start) * 1000)
    return ProcResult(
        returncode=proc.returncode or 0,
        stdout=(out or b"").decode("utf-8", errors="replace"),
        stderr=(err or b"").decode("utf-8", errors="replace"),
        duration_ms=dur,
        found=True,
    )
