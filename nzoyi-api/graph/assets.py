"""Asset graph — deduplicated inventory of discovered targets.

Mirrors the ``assets`` table (Phase 1). In-memory for Phase 2; a persistent
repository is wired in a later phase. The dedup key guarantees the scope gate
and coverage views reason over a single canonical asset per (type, value).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

ASSET_TYPES = ("domain", "subdomain", "ip", "service", "endpoint")


def dedup_key(asset_type: str, value: str, parent: str | None = None) -> str:
    base = f"{asset_type}:{value.lower().strip()}"
    return f"{base}@{parent}" if parent else base


@dataclass
class Asset:
    id: str
    type: str
    value: str
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AssetGraph:
    def __init__(self) -> None:
        self._by_key: dict[str, Asset] = {}
        self._by_id: dict[str, Asset] = {}

    def add(
        self,
        asset_type: str,
        value: str,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Asset:
        if asset_type not in ASSET_TYPES:
            raise ValueError(f"type d'actif invalide: {asset_type}")
        parent_val = self._by_id[parent_id].value if parent_id in self._by_id else None
        key = dedup_key(asset_type, value, parent_val)
        if key in self._by_key:
            existing = self._by_key[key]
            if metadata:
                existing.metadata.update(metadata)
            return existing
        asset = Asset(
            id=str(uuid.uuid4()),
            type=asset_type,
            value=value,
            parent_id=parent_id,
            metadata=metadata or {},
        )
        self._by_key[key] = asset
        self._by_id[asset.id] = asset
        return asset

    def all(self) -> list[Asset]:
        return list(self._by_id.values())

    def get(self, asset_id: str) -> Asset | None:
        return self._by_id.get(asset_id)

    def values(self) -> set[str]:
        return {a.value for a in self._by_id.values()}
