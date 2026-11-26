"""Secret manager — secrets encrypted at rest with AES-256-GCM (brief 7.6).

Key resolution order:
  1. ``NZOYI_SECRET_KEY`` env var (32 bytes, base64 or hex).
  2. ``keys/secret.key`` (generated on first use, mode 0600).

Stored values (LLM keys, proxies, task credentials) are never returned in clear
by the API — only their names. The service refuses to decrypt if encrypted
secrets exist but no key is available.
"""

from __future__ import annotations

import base64
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY_PATH = Path(os.environ.get("NZOYI_KEYS_DIR", "keys")) / "secret.key"


class SecretError(RuntimeError):
    pass


def _load_key() -> bytes:
    env = os.environ.get("NZOYI_SECRET_KEY")
    if env:
        raw = env.strip()
        try:
            key = base64.b64decode(raw) if len(raw) not in (64,) else bytes.fromhex(raw)
        except Exception:  # noqa: BLE001
            try:
                key = bytes.fromhex(raw)
            except ValueError as exc:
                raise SecretError("NZOYI_SECRET_KEY invalide (base64/hex 32 bytes).") from exc
        if len(key) != 32:
            raise SecretError("NZOYI_SECRET_KEY doit faire 32 bytes.")
        return key
    # File-based key, generated once with tight permissions.
    if _KEY_PATH.is_file():
        return _KEY_PATH.read_bytes()
    _KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    key = AESGCM.generate_key(bit_length=256)
    _KEY_PATH.write_bytes(key)
    try:
        os.chmod(_KEY_PATH, 0o600)
    except OSError:
        pass
    return key


@dataclass
class _Secret:
    name: str
    blob: bytes  # nonce(12) || ciphertext
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SecretManager:
    def __init__(self) -> None:
        self._store: dict[str, _Secret] = {}
        self._lock = threading.RLock()
        self._key: bytes | None = None

    def _aes(self) -> AESGCM:
        if self._key is None:
            self._key = _load_key()
        return AESGCM(self._key)

    def set(self, name: str, value: str) -> dict[str, str]:
        aes = self._aes()
        nonce = os.urandom(12)
        ct = aes.encrypt(nonce, value.encode("utf-8"), name.encode("utf-8"))
        with self._lock:
            s = _Secret(name=name, blob=nonce + ct)
            self._store[name] = s
        return {"name": name, "created_at": s.created_at}

    def get(self, name: str) -> str:
        with self._lock:
            s = self._store.get(name)
        if s is None:
            raise SecretError(f"secret inconnu: {name}")
        aes = self._aes()
        nonce, ct = s.blob[:12], s.blob[12:]
        return aes.decrypt(nonce, ct, name.encode("utf-8")).decode("utf-8")

    def list(self) -> list[dict[str, str]]:
        with self._lock:
            return [{"name": s.name, "created_at": s.created_at}
                    for s in sorted(self._store.values(), key=lambda x: x.name)]

    def delete(self, name: str) -> bool:
        with self._lock:
            return self._store.pop(name, None) is not None

    def startup_check(self) -> None:
        """Refuse to run with encrypted secrets but no usable key."""
        with self._lock:
            has_secrets = bool(self._store)
        if has_secrets:
            self._aes()  # raises if no key


GLOBAL_SECRETS = SecretManager()
