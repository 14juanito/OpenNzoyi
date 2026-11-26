# NZOYI — Architecture (en construction)

> Statut : NZOYI passe de banc de mesure académique à **outil d'audit autonome**.
> Les **7 phases** de la refonte sont implémentées ; ce document décrit
> l'architecture livrée, phase par phase.

## Vue d'ensemble (cible)

```
nzoyi-core/   microservice RL (FastAPI)      — moteur d'évasion, SANS LLM
nzoyi-api/    orchestrateur + agents + outils + gates (à venir, Phase 2+)
nzoyi-web/    UI Next.js (à venir, Phase 5)
db/           migrations Alembic (schéma partagé PostgreSQL)
```

---

## Phase 1 — Extraction du moteur RL (IMPLÉMENTÉE)

### Décisions d'architecture et justifications

**1. Copie byte-identique du Q-Learning, pas un déplacement.**
Le brief demande de « déplacer `q_learner.py` sans modification ». Vérification
faite : **13 sites** importent `nzoyi.rl.qlearning` (agents `evasion`/
`orchestrator`, `training/offline.py`, et surtout `tests/test_validation.py`).
Un déplacement casserait les 72 tests et le pipeline existant — ce qui viole le
critère d'acceptation n°1 (72 tests verts) et le principe de non-régression.

Décision : `nzoyi/rl/qlearning.py` **reste en place** ; `nzoyi-core/evasion/
q_learner.py` en est une **copie SHA256-identique**. L'algorithme n'est modifié
dans aucune des deux copies. À terme (Phase 2+), les agents consommateurs
pourront migrer vers le microservice, et la copie `nzoyi/rl/` deviendra la
baseline de recherche figée.

Vérifiable :
```
diff nzoyi/rl/qlearning.py nzoyi-core/evasion/q_learner.py   # vide
sha256sum nzoyi/rl/qlearning.py nzoyi-core/evasion/q_learner.py  # identiques
```

**2. Nouvel espace état/action SANS réécrire le learner.**
Le brief définit un espace d'état riche (1512 états) et un espace d'action par
phase `{tool, timing, delay, frag}`, incompatibles avec l'`EvasionState`
historique (72 états) et les 4 actions-delta de `EvasionAction`.

Le `EvasionQLearner` est resté **générique** : sa Q-table est un
`dict[str, float]` keyé par `f"{state.as_key()}:{action.name}"`. On l'exploite
donc sans le toucher :

- `state.py` : espace explicite + `state_hash()` réversible (index ordinaux
  joints par `.`). Un `_KeyState` minimal expose `.as_key()` = ce hash.
- `action.py` : espace par phase + `action_hash()` réversible
  (`tool.timing.delay.frag`). `phase_actions(phase)` renvoie le tuple
  `EvasionAction(name=<action_hash>)` passé en `actions=` au learner.
- Les délimiteurs internes (`.`) évitent le `:` que le learner utilise comme
  séparateur composite → round-trip garanti.

Résultat : la **pure logique tabulaire** (`update`, `_q`, décroissance epsilon)
tourne inchangée sur le nouvel espace. `apply_action` (modèle delta) n'est tout
simplement pas utilisé par l'API opérationnelle.

**3. Persistance (`policy_store.py`).**
Q-values persistées par `(task_id, phase, state_hash, action_hash)` dans la table
`q_tables` (upsert `ON CONFLICT`). Fallback `MemoryPolicyStore` déterministe si
`NZOYI_DATABASE_URL` est absent → le service démarre et se teste sans base
(principe : pas de dépendance réseau dure).

**4. Microservice (`api.py`).**
Service **stateless** : chaque requête charge la tranche de Q-table utile,
applique le learner, réécrit les cellules mutées. Aucune importation LLM
(contrainte vérifiée par `scripts/verify.sh`).

| Endpoint | Rôle |
|---|---|
| `POST /evasion/next_action` | `{task_id,state,phase}` → `{tool,timing,delay,frag,action_hash}` (epsilon-greedy) |
| `POST /evasion/update` | `{task_id,state,action_hash,reward,next_state}` → cellule Q mise à jour |
| `GET /evasion/policy/{task_id}?phase=` | résumé de la Q-table |
| `POST /evasion/reset/{task_id}` | purge la politique d'une tâche |
| `GET /health` | état + backend de persistance + taille d'espace |

> Note Phase 1 : la décroissance d'epsilon n'est pas encore persistée entre
> requêtes (le service étant stateless) — epsilon est piloté par
> `NZOYI_RL_EPSILON`. La persistance de l'exploration est un sujet Phase 2.

### Base de données

Migration Alembic initiale (`db/migrations/versions/0001_initial_schema.py`) :
13 tables du brief (`tasks`, `assets`, `nodes`, `edges`, `anchors`, `todolist`,
`agent_runs`, `evidence`, `findings`, `q_tables`, `approval_rules`, `approvals`,
`secrets`), Postgres-native (UUID, JSONB, BYTEA, `gen_random_uuid`, CHECK).
Migration **réversible** (upgrade/downgrade validés sur PostgreSQL 16).

### Vérification Phase 1

```
bash scripts/verify.sh
#   [1/3] 72 passed
#   [2/3] 0 référence LLM dans nzoyi-core/evasion/*.py
#   [3/3] smoke RL OK (health + next_action + update)
```

Migrations (nécessite un PostgreSQL et `NZOYI_DATABASE_URL`) :
```
cd db && NZOYI_DATABASE_URL=postgresql://... python3 -m alembic upgrade head
```

---

## Phase 2 — Orchestrateur (nzoyi-api)

Boucle `graph change → Planner → intent queue → Dispatcher → write-back`.

- **Tool / ToolResult / ToolRegistry** (`tools/`) : contrat unique, wrappers
  minces autour de binaires standard, `run_subprocess` async avec dégradation
  `skipped` si binaire absent.
- **Graphe unique** (`graph/`) : exploration (nodes goal/intent/fact/finding/
  hint, edges spawns/derived_from/yields/proves) + assets (dédup). Remplace le
  PTT — une seule mémoire.
- **Planner** : stratégie (phase, cible), un intent à la fois.
- **Dispatcher** : scope → interception → budget → `rl.next_action` →
  governor.clamp → `tool.run` → evidence → reward → `rl.update` → write-back.
  Le RL choisit outil + timing + delay + frag ; le Planner décide la phase.
- **rl_client** : HTTP vers `nzoyi-core` (`NZOYI_CORE_URL`) ou in-process.
- **engine + main.py** (CLI) + **server.py** (API HTTP + SSE).

## Phase 3 — Catalogue d'outils P0/P1

15 wrappers : recon (nmap, rustscan, httpx, subfinder), vuln (nuclei, ffuf,
sqlmap, nikto), ad_enum (netexec, impacket, bloodhound, sharphound), linux
(linpeas, linux-exploit-suggester), lateral (chisel). `knowledge/
tool_signatures.py` : prior de détection pour amorcer le RL.

## Phase 4 — Garde-fous & preuves

`gates/` : scope, interception (règles string/regex/argv_prefix, modes
autonome/semi), budget (wrap-up), untrusted boundary, lifecycle (kill +
rollback). `agents/noise_governor.py` : borne le débit du RL (token bucket,
jitter, backoff). `evidence/` : capture + addon mitmproxy (port 8788).
`scripts/restore_lab.sh` : snapshots libvirt. Voir [SECURITY.md](SECURITY.md).

## Phase 5 — UI (nzoyi-web)

Next.js 15 (App Router) + Tailwind, palette OpenNzoyi (orange/noir/blanc).
Dashboard, `/tasks/new`, `/tasks/[id]` (live SSE), `/tasks/[id]/findings`.
Backend : endpoints `/api/*` + flux SSE `/api/tasks/{id}/stream`.

## Phase 6 — Outils P2 & packaging

Wrappers post/lateral/evasion (certipy, evil-winrm, rubeus, mimikatz, winpeas,
sdn-toolkit, scapy_evasion) — destructifs gatés. `docker-compose.yml` :
db (postgres:16) + core + api + web ; migrations appliquées au démarrage.

## Vérification globale

```
bash scripts/verify.sh        # 72 tests d'origine + gate LLM + smoke RL + 45 tests nzoyi-api
docker compose config         # stack valide
cd nzoyi-web && npm run build  # UI compile + typecheck
```
