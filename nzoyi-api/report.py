"""Audit report builder — serializes a task's graph into a verifiable JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from graph.assets import AssetGraph
from graph.exploration import ExplorationGraph

_SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def build_report(
    task: dict[str, Any],
    graph: ExplorationGraph,
    assets: AssetGraph,
) -> dict[str, Any]:
    findings = []
    for n in graph.findings():
        findings.append(
            {
                "id": n.id,
                "title": n.content.get("title"),
                "severity": n.content.get("severity", "info"),
                "matched_at": n.content.get("matched_at"),
                "tool": n.content.get("tool"),
                "status": "unverified",
            }
        )
    findings.sort(key=lambda f: _SEV_ORDER.get(f["severity"], 0), reverse=True)

    sev_counts: dict[str, int] = {}
    for f in findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1

    return {
        "task": {
            "id": task.get("id"),
            "name": task.get("name"),
            "target": task.get("target"),
            "scope": task.get("scope"),
            "profile": task.get("profile", "balanced"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "assets": len(assets.all()),
            "facts": len(graph.nodes_of("fact")),
            "findings_total": len(findings),
            "findings_by_severity": sev_counts,
        },
        "assets": [
            {"id": a.id, "type": a.type, "value": a.value, "metadata": a.metadata}
            for a in assets.all()
        ],
        "findings": findings,
        "graph": graph.to_dict(),
    }


def write_report(report: dict[str, Any], path: str) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    return path
