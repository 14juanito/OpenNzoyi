"""Exploration graph — the single shared memory of a task.

Nodes: goal / intent / fact / finding / hint.
Edges: spawns / derived_from / yields / proves.

This replaces the historical PTT blackboard: there is exactly ONE graph, not a
graph plus a separate tree. The Planner reads facts and emits intents; the
Dispatcher executes intents and writes facts/findings back, linking each with an
edge so provenance is always traceable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable

NODE_TYPES = ("goal", "intent", "fact", "finding", "hint")
EDGE_RELATIONS = ("spawns", "derived_from", "yields", "proves")


@dataclass
class Node:
    id: str
    type: str
    content: dict[str, Any]
    status: str = "open"
    agent: str | None = None
    anchors: set[str] = field(default_factory=set)  # asset ids


@dataclass
class Edge:
    source_id: str
    target_id: str
    relation: str


class ExplorationGraph:
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []

    # ── nodes ────────────────────────────────────────────────────────────
    def add_node(
        self,
        node_type: str,
        content: dict[str, Any],
        status: str = "open",
        agent: str | None = None,
        anchors: Iterable[str] | None = None,
    ) -> Node:
        if node_type not in NODE_TYPES:
            raise ValueError(f"type de nœud invalide: {node_type}")
        node = Node(
            id=str(uuid.uuid4()),
            type=node_type,
            content=content,
            status=status,
            agent=agent,
            anchors=set(anchors or ()),
        )
        self._nodes[node.id] = node
        return node

    def get(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def set_status(self, node_id: str, status: str) -> None:
        if node_id in self._nodes:
            self._nodes[node_id].status = status

    def nodes_of(self, node_type: str, status: str | None = None) -> list[Node]:
        out = [n for n in self._nodes.values() if n.type == node_type]
        if status is not None:
            out = [n for n in out if n.status == status]
        return out

    # ── edges ────────────────────────────────────────────────────────────
    def add_edge(self, source_id: str, target_id: str, relation: str) -> Edge:
        if relation not in EDGE_RELATIONS:
            raise ValueError(f"relation invalide: {relation}")
        edge = Edge(source_id=source_id, target_id=target_id, relation=relation)
        self._edges.append(edge)
        return edge

    def edges(self) -> list[Edge]:
        return list(self._edges)

    # ── views ────────────────────────────────────────────────────────────
    def findings(self) -> list[Node]:
        return self.nodes_of("finding")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "content": n.content,
                    "status": n.status,
                    "agent": n.agent,
                    "anchors": sorted(n.anchors),
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {"source": e.source_id, "target": e.target_id, "relation": e.relation}
                for e in self._edges
            ],
        }
