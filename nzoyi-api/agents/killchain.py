"""Kill-chain reconstruction from the exploration graph.

Walks the provenance edges (goal -spawns-> intent -yields-> fact -proves->
finding) to produce an ordered attack chain and a narrative summary — the
equivalent of a pentest "attack path".
"""

from __future__ import annotations

from typing import Any


def reconstruct(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    # adjacency by relation
    yields: dict[str, list[str]] = {}
    proves: dict[str, list[str]] = {}
    for e in edges:
        if e["relation"] == "yields":
            yields.setdefault(e["source"], []).append(e["target"])
        elif e["relation"] == "proves":
            proves.setdefault(e["source"], []).append(e["target"])

    steps: list[dict[str, Any]] = []
    order = 0
    for n in graph.get("nodes", []):
        if n["type"] != "intent":
            continue
        order += 1
        phase = n["content"].get("phase", "?")
        target = n["content"].get("target", "")
        fact_ids = yields.get(n["id"], [])
        result = "aucun résultat"
        findings: list[dict[str, str]] = []
        for fid in fact_ids:
            fact = nodes.get(fid, {})
            kind = fact.get("content", {}).get("kind", "")
            svc = fact.get("content", {}).get("services", [])
            shares = fact.get("content", {}).get("shares", [])
            bits = []
            if svc:
                bits.append(f"{len(svc)} service(s)")
            if shares:
                bits.append(f"{len(shares)} partage(s)")
            result = f"{kind}: " + (", ".join(bits) if bits else "collecté")
            for sid in proves.get(fid, []):
                fn = nodes.get(sid, {}).get("content", {})
                findings.append({"title": fn.get("title", "?"),
                                 "severity": fn.get("severity", "info")})
        steps.append({
            "order": order, "phase": phase, "target": target,
            "action": f"{phase} sur {target}", "result": result,
            "findings": findings,
        })

    phases = [s["phase"] for s in steps]
    n_find = sum(len(s["findings"]) for s in steps)
    summary = (
        " → ".join(phases) + f" · {len(steps)} étape(s), {n_find} finding(s)"
        if steps else "Chaîne vide — aucun intent exécuté."
    )
    return {"steps": steps, "summary": summary, "length": len(steps)}
