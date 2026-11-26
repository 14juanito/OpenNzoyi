# NZOYI — Architecture (en construction)

> Statut : NZOYI passe de banc de mesure académique à **outil d'audit autonome**.
> Ce document est rempli phase par phase. Seule la **Phase 1** est implémentée à
> ce jour ; les sections suivantes décrivent la cible et seront complétées au fur
> et à mesure.

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

## Phases suivantes (non implémentées)

- **Phase 2** : Planner + Dispatcher + 3 outils (nmap, nuclei, netexec), boucle
  end-to-end.
- **Phase 3** : catalogue d'outils P0/P1.
- **Phase 4** : proxy MITM + gates (scope, interception, budget) + restore_lab.
- **Phase 5** : UI Next.js (design system OpenZoyi).
- **Phase 6** : outils P2 + packaging Docker Compose.
