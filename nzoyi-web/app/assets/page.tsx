"use client";
import { useEffect, useState } from "react";
import { api, Task } from "@/lib/api";

export default function AssetsPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  useEffect(() => { api.listTasks().then(setTasks).catch(() => {}); }, []);
  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Actifs</h1>
        <p className="text-sm text-nzoyi-slate">Couverture des actifs découverts par tâche</p>
      </div>
      <div className="card">
        {tasks.length === 0 ? (
          <p className="py-8 text-center text-sm text-nzoyi-slate">Aucune tâche.</p>
        ) : (
          <ul className="divide-y divide-nzoyi-border/60">
            {tasks.map((t) => (
              <li key={t.id} className="flex items-center justify-between py-3">
                <div>
                  <a href={`/tasks/${t.id}`} className="font-medium hover:text-nzoyi-orange">{t.name}</a>
                  <p className="font-mono text-xs text-nzoyi-slate">{t.target}</p>
                </div>
                <a href={`/tasks/${t.id}`} className="text-sm text-nzoyi-orange hover:underline">
                  Voir le graphe →
                </a>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-xs text-nzoyi-slate">
          La couverture (testé / non testé / hors scope) s'affiche dans l'onglet
          « Graphe » d'une tâche.
        </p>
      </div>
    </div>
  );
}
