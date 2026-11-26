# nzoyi-web

Interface d'audit OpenNzoyi — Next.js 15 (App Router) + TypeScript + Tailwind.
Palette extraite du logo OpenNzoyi (orange `#F59E0B`, noir `#1F2937`, blanc).

## Démarrage

```bash
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev        # http://localhost:3000
```

Le backend `nzoyi-api` doit tourner :

```bash
cd ../nzoyi-api && uvicorn server:app --port 8000
```

## Écrans (P0 livrés)

| Route | Rôle |
|-------|------|
| `/` | Dashboard (cartes de résumé, tâches récentes, état système) |
| `/tasks/new` | Création d'une tâche (cible, scope, profil, budgets) |
| `/tasks/[id]` | Vue live (flux SSE des tool calls, compteurs, score) |
| `/tasks/[id]/findings` | Tableau des findings (sévérité, preuve, export JSON) |

Écrans P1/P2 (graphe React Flow, couverture d'actifs, trafic/replay,
approbations, réglages LLM) : à venir — les entrées de la sidebar les
anticipent.

## Build

```bash
npm run build      # vérifié : compile + typecheck OK (Next.js 15.5.29)
```
