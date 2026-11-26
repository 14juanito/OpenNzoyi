"""Niveau 1 — cerveau stratégique LLM pour le Planner.

Le LLM décide la PROCHAINE étape (phase + cible) à partir de l'état du graphe
d'exploration. C'est strictement *stratégique* : il ne calcule jamais de
récompense ni d'action d'évasion (cela reste au RL). Deux invariants :

* **Repli déterministe** : sans backend LLM (pas de clé, échec, sortie
  invalide), on retombe sur le Planner à base de règles — jamais d'exception.
* **Frontière untrusted** : l'état du graphe (données issues d'outils) est
  encadré par des marqueurs à nonce ; le prompt système interdit d'y voir des
  instructions. Le RL n'est jamais concerné (aucun LLM dans sa boucle).

Réutilise le panel LLM existant (``nzoyi.llm.backend_resolver.resolve_backend``).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from agents.planner import Intent, Planner
from agents.main_agent import summarize_graph
from gates.untrusted_output import SYSTEM_PREAMBLE, wrap_untrusted
from graph.assets import AssetGraph
from graph.exploration import ExplorationGraph

logger = logging.getLogger("nzoyi.agents.llm_planner")

# Le panel LLM vit à la racine du dépôt (package `nzoyi`).
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:  # repli silencieux si le panel n'est pas importable
    from nzoyi.llm.backend import LLMBackend, LLMBackendError
    from nzoyi.llm.backend_resolver import resolve_backend
except Exception:  # noqa: BLE001
    LLMBackend = object  # type: ignore
    LLMBackendError = Exception  # type: ignore
    resolve_backend = None  # type: ignore

_VALID_PHASES = {"recon", "vuln", "ad_enum", "linux", "lateral", "post"}

SYSTEM_PROMPT = (
    "Tu es le cerveau STRATÉGIQUE d'un pentest de lab isolé et AUTORISÉ. "
    "À partir de l'état d'exploration, choisis LA prochaine étape. Tu ne "
    "calcules jamais de récompense ni d'action d'évasion (cela reste au RL). "
    + SYSTEM_PREAMBLE +
    " Réponds UNIQUEMENT en JSON, sans aucun texte autour, avec exactement ce "
    'schéma : {"phase": "recon|vuln|ad_enum|linux|lateral|post", '
    '"target": "<ip|url|domaine déjà découvert ou cible racine>", '
    '"rationale": "<courte justification>"}.'
)


class LLMPlanner:
    """Planner piloté par LLM, avec repli sur le Planner déterministe."""

    def __init__(
        self,
        graph: ExplorationGraph,
        assets: AssetGraph,
        scope: dict[str, Any],
        root_target: str,
        backend: Any = None,
    ) -> None:
        self.graph = graph
        self.assets = assets
        self.scope = scope
        self.root_target = root_target
        self._fallback = Planner(graph, assets)
        self.backend = self._resolve(backend)

    @staticmethod
    def _resolve(explicit: Any) -> Any:
        if explicit is not None:
            return explicit
        if resolve_backend is None:
            return None
        try:
            backend, _provider, _model = resolve_backend(
                explicit_backend=None, model_override=None, temperature=0.0,
                default_model="claude-sonnet-5", env_prefix="ANTHROPIC",
            )
            return backend
        except Exception:  # noqa: BLE001
            return None

    def plan(self) -> list[Intent]:
        # 1) Les hints de l'opérateur et le repli restent déterministes : si le
        #    Planner à règles a déjà quelque chose de prioritaire (hint, recon
        #    initial), on l'honore tel quel.
        if self.backend is None or self.graph.nodes_of("hint", status="open"):
            return self._fallback.plan()
        try:
            intent = self._llm_next()
        except Exception as exc:  # noqa: BLE001 — repli déterministe garanti
            logger.warning("LLMPlanner: repli déterministe (%s)", exc)
            return self._fallback.plan()
        if intent is None:
            return self._fallback.plan()
        return [intent]

    # ── LLM ──────────────────────────────────────────────────────────────
    def _llm_next(self) -> Intent | None:
        goals = self.graph.nodes_of("goal", status="open")
        if not goals:
            return None
        goal = goals[0]
        summary = summarize_graph(self.graph.to_dict())
        known = sorted(self.assets.values())
        user = (
            f"Cible racine : {self.root_target}\n"
            f"Scope : {json.dumps(self.scope)}\n"
            f"Actifs découverts : {json.dumps(known)}\n"
            "État d'exploration :\n"
            + wrap_untrusted(json.dumps(summary, ensure_ascii=False))
            + "\nChoisis la prochaine étape (ou phase=post si tout est couvert)."
        )
        raw = self.backend.decide(SYSTEM_PROMPT, user)
        data = _parse_json(raw)
        if not data:
            return None
        phase = str(data.get("phase", "")).strip()
        target = str(data.get("target", "")).strip() or self.root_target
        if phase not in _VALID_PHASES:
            return None
        # Anti-invention : la cible doit être la racine ou un actif découvert.
        host = target.split("://")[-1].split("/")[0].split(":")[0]
        if host != self.root_target and host not in self.assets.values():
            return None
        node = self.graph.add_node(
            "intent",
            {"phase": phase, "target": target, "rationale": data.get("rationale", ""),
             "from_llm": True},
            status="open", agent="llm-planner",
        )
        self.graph.add_edge(goal.id, node.id, "spawns")
        return Intent(phase=phase, target=target, goal_node_id=goal.id,
                      intent_node_id=node.id)


def _parse_json(raw: str) -> dict[str, Any] | None:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(raw[start:end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None
