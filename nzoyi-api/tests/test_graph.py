"""Exploration + asset graph tests."""

import pytest

from graph.assets import AssetGraph
from graph.exploration import ExplorationGraph


def test_asset_dedup():
    g = AssetGraph()
    a1 = g.add("ip", "192.168.100.11")
    a2 = g.add("ip", "192.168.100.11")
    assert a1.id == a2.id
    assert len(g.all()) == 1


def test_asset_invalid_type():
    with pytest.raises(ValueError):
        AssetGraph().add("planet", "mars")


def test_graph_nodes_edges_and_views():
    g = ExplorationGraph("t1")
    goal = g.add_node("goal", {"target": "x"})
    intent = g.add_node("intent", {"phase": "recon"})
    g.add_edge(goal.id, intent.id, "spawns")
    fact = g.add_node("fact", {"kind": "recon"})
    g.add_edge(intent.id, fact.id, "yields")
    finding = g.add_node("finding", {"title": "bug", "severity": "high"})
    g.add_edge(fact.id, finding.id, "proves")

    assert len(g.findings()) == 1
    assert len(g.edges()) == 3
    assert g.to_dict()["task_id"] == "t1"


def test_graph_invalid_relation():
    g = ExplorationGraph("t1")
    a = g.add_node("goal", {})
    b = g.add_node("fact", {})
    with pytest.raises(ValueError):
        g.add_edge(a.id, b.id, "teleports")
