# NZOYI — Sécurité & usage responsable

NZOYI est un **outil d'audit offensif autonome** destiné **exclusivement** aux
tests de pénétration **autorisés** sur un périmètre **que vous contrôlez**
(lab KVM/libvirt isolé, réseau `nzoyi-lab` sans egress — voir
[`LAB_SETUP.md`](LAB_SETUP.md)). Toute utilisation contre des systèmes sans
autorisation écrite explicite est interdite.

## Garde-fous techniques (défense en profondeur)

| Garde-fou | Rôle | Implémentation |
|-----------|------|----------------|
| **Scope gate** | Refuse toute cible hors CIDR/domaine déclaré + anti-invention (cible découverte ou racine) | `nzoyi-api/gates/scope_gate.py` |
| **Interception gate** | Actions destructrices (dcsync, lsass_dump, mimikatz, secretsdump, persistance…) gatées ; modes autonome / semi-autonome ; règles string/regex/argv_prefix | `nzoyi-api/gates/interception_gate.py` |
| **Budget** | Plafond tokens/turns, wrap-up forcé | `nzoyi-api/gates/budget.py` |
| **Untrusted boundary** | Sorties d'outils encadrées par marqueurs à nonce (données, jamais instructions) — protège les couches LLM | `nzoyi-api/gates/untrusted_output.py` |
| **Noise governor** | Plafonne le débit réseau par profil ; **borne** le RL (clamp) | `nzoyi-api/agents/noise_governor.py` |
| **Kill dur + rollback** | Annule les workers et défait les persistances installées | `nzoyi-api/gates/lifecycle.py` |
| **Restore lab** | Remet les VMs à leurs snapshots propres | `scripts/restore_lab.sh` |

Le moteur d'évasion (RL) est **libre** d'optimiser objectif + discrétion ;
ce sont les *gates* (code déterministe), pas une récompense, qui empêchent les
actions hors scope ou destructrices. Le RL n'appelle **jamais** de LLM
(vérifié par `scripts/verify.sh`).

## Les « outils » sont des wrappers

Le catalogue (`nzoyi-api/tools/implementations/`) ne contient **aucun payload
offensif** : chaque classe est un wrapper mince qui invoque un binaire standard
(nmap, nuclei, netexec, impacket, mimikatz, …) que l'opérateur installe dans le
lab, et en parse la sortie. Sans le binaire, le wrapper retourne `skipped`.

## Secrets au repos

- Clé AES-256-GCM dans `keys/secret.key` (0600) ou `NZOYI_SECRET_KEY`.
- Toutes les clés LLM / proxies / credentials de tâche sont chiffrés
  (table `secrets`). Refus de démarrer si des secrets chiffrés existent sans
  clé disponible.
- Aucune clé réelle dans `.env.example` ; `.env` est git-ignoré.

## Preuves

Chaque finding porte une preuve capturée (requête + réponse) via le proxy MITM
(`evidence/mitm_proxy.py`, port 8788), liée au finding dans la table `evidence`.

## Signalement

Vulnérabilité dans NZOYI lui-même : ouvrez une issue privée ou contactez le
mainteneur. N'incluez jamais de données réelles de cible dans un rapport public.
