"""Niveau 1 — LLMPlanner : chemin LLM + repli déterministe."""

from agents.llm_planner import LLMPlanner
from graph.assets import AssetGraph
from graph.exploration import ExplorationGraph


class FakeBackend:
    def __init__(self, reply: str):
        self.reply = reply
        self.calls = 0

    def decide(self, system_prompt: str, user_message: str) -> str:
        self.calls += 1
        return self.reply


def _setup():
    g = ExplorationGraph("t1")
    g.add_node("goal", {"target": "192.168.100.11", "objective": "audit"}, status="open")
    a = AssetGraph()
    a.add("ip", "192.168.100.11")
    return g, a


def test_llm_planner_uses_backend_decision():
    g, a = _setup()
    be = FakeBackend('{"phase":"recon","target":"192.168.100.11","rationale":"start"}')
    p = LLMPlanner(g, a, {"cidrs": ["192.168.100.0/24"], "domains": []},
                   "192.168.100.11", backend=be)
    intents = p.plan()
    assert be.calls == 1
    assert len(intents) == 1 and intents[0].phase == "recon"
    # intent node tagged as LLM-originated
    node = g.get(intents[0].intent_node_id)
    assert node.content.get("from_llm") is True


def test_llm_planner_rejects_invented_target_then_falls_back():
    g, a = _setup()
    # LLM tries an out-of-assets target → rejected → deterministic fallback
    be = FakeBackend('{"phase":"recon","target":"10.9.9.9"}')
    p = LLMPlanner(g, a, {"cidrs": ["192.168.100.0/24"], "domains": []},
                   "192.168.100.11", backend=be)
    intents = p.plan()
    # fallback planner still emits a recon intent on the real target
    assert len(intents) == 1 and intents[0].target == "192.168.100.11"


def test_llm_planner_no_backend_is_deterministic():
    g, a = _setup()
    p = LLMPlanner(g, a, {"cidrs": ["192.168.100.0/24"], "domains": []},
                   "192.168.100.11", backend=None)
    # Force no resolved backend (offline / no key)
    p.backend = None
    intents = p.plan()
    assert len(intents) == 1 and intents[0].phase == "recon"


def test_llm_planner_bad_json_falls_back():
    g, a = _setup()
    be = FakeBackend("désolé je ne peux pas")
    p = LLMPlanner(g, a, {"cidrs": ["192.168.100.0/24"], "domains": []},
                   "192.168.100.11", backend=be)
    intents = p.plan()
    assert len(intents) == 1 and intents[0].phase == "recon"  # fallback
