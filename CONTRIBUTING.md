# Contribuer à OpenNzoyi

Merci de t'intéresser à **OpenNzoyi** 🐝 — un outil d'audit de sécurité
**autonome** multi-agents, avec un moteur d'évasion des IDS par **apprentissage
par renforcement** (RL), et une contrainte d'architecture stricte : **aucun LLM
dans la boucle d'évasion**.

Le projet est jeune et **cherche des contributeurs**. Que tu sois pentester,
chercheur en ML/RL, dev backend/frontend ou admin de lab, il y a de quoi faire.

## ⚠️ Cadre éthique (non négociable)

OpenNzoyi est destiné **exclusivement** aux tests de pénétration **autorisés**
sur un lab **isolé que tu contrôles**. Toute contribution doit respecter ce
cadre (voir [`LICENSE`](LICENSE) et [`docs/SECURITY.md`](docs/SECURITY.md)) :
- jamais de payload offensif embarqué (les outils sont des **wrappers** autour
  de binaires standard) ;
- ne jamais affaiblir les garde-fous (scope gate, interception gate, limites de
  débit, journalisation) ;
- pas de cible réelle non consentie, jamais.

## Où contribuer (par profil)

| Profil | Pistes |
|--------|--------|
| **Pentester / Red team** | nouveaux wrappers d'outils, parsers robustes, playbooks de phase, validation en lab |
| **ML / RL** | améliorer le Q-Learning (reward shaping, état/action), évaluer la convergence, comparer à d'autres détecteurs (UNSW-NB15) |
| **Backend (Python/FastAPI)** | persistance PostgreSQL, concurrence, retests réels, moteur OOB/OAST |
| **Frontend (Next.js/TS)** | vues manquantes (credentials, retests), graphes, UX |
| **Détection / Blue team** | ingestion Suricata/Zeek/Sysmon, signatures, mesure d'évasion réelle |
| **Lab / DevOps** | KVM/libvirt, cibles vulnérables, Docker, CI |

Cherche les issues étiquetées `good first issue` et `help wanted`.

## Démarrer en local

```bash
git clone https://github.com/14juanito/Projet-Nzoyi.git
cd Projet-Nzoyi

# microservice RL + orchestrateur
pip install -r nzoyi-core/requirements.txt -r nzoyi-api/requirements.txt
bash scripts/verify.sh          # 72 tests d'origine + gate LLM + tests nzoyi-api

# UI
cd nzoyi-web && npm install && npm run dev
```

## Standards de code

- **Les 72 tests de validation d'origine doivent rester verts** à chaque PR
  (non-régression) : `pytest tests/test_validation.py`.
- **Gate LLM** : `grep -rn "llm" nzoyi-core/evasion/` doit renvoyer **0**. Aucun
  LLM ne touche la boucle d'évasion, jamais.
- **Repli déterministe** : toute couche LLM-isée doit retomber sur un
  comportement déterministe si le modèle est absent/échoue.
- Python : type hints, docstrings, pas de duplication. TS : `npm run build` doit
  passer (typecheck).
- Un PR = un sujet. Décris le *pourquoi*, pas seulement le *quoi*.

## Processus

1. Fork + branche (`feat/...`, `fix/...`).
2. Code + tests. `bash scripts/verify.sh` au vert.
3. PR claire, liée à une issue si possible.

Questions / idées → ouvre une **Discussion** ou une **issue**. Bienvenue à bord 🐝
