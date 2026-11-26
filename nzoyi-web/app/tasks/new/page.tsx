"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function NewTask() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "audit",
    target: "192.168.100.11",
    cidrs: "192.168.100.0/24",
    domains: "",
    profile: "balanced",
    budget_tokens: "",
    budget_turns: "",
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const task = await api.createTask({
        name: form.name,
        target: form.target,
        profile: form.profile as any,
        scope: {
          cidrs: form.cidrs.split(",").map((s) => s.trim()).filter(Boolean),
          domains: form.domains.split(",").map((s) => s.trim()).filter(Boolean),
        },
        budget_tokens: form.budget_tokens ? Number(form.budget_tokens) : null,
        budget_turns: form.budget_turns ? Number(form.budget_turns) : null,
      });
      router.push(`/tasks/${task.id}`);
    } catch (err: any) {
      setError(err.message || "Échec de la création");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-2xl font-bold">Nouvelle tâche d'audit</h1>
      <p className="mb-6 text-sm text-nzoyi-slate">
        Définissez la cible, le périmètre autorisé et le profil de discrétion.
      </p>

      <form onSubmit={submit} className="card space-y-5">
        <div>
          <label className="label">Nom</label>
          <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} />
        </div>
        <div>
          <label className="label">Cible</label>
          <input className="input font-mono" value={form.target}
                 onChange={(e) => set("target", e.target.value)} placeholder="192.168.100.11" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Scope — CIDR (séparés par ,)</label>
            <input className="input font-mono" value={form.cidrs}
                   onChange={(e) => set("cidrs", e.target.value)} />
          </div>
          <div>
            <label className="label">Scope — domaines</label>
            <input className="input font-mono" value={form.domains}
                   onChange={(e) => set("domains", e.target.value)} placeholder="example.com" />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="label">Profil</label>
            <select className="input" value={form.profile} onChange={(e) => set("profile", e.target.value)}>
              <option value="quiet">quiet</option>
              <option value="balanced">balanced</option>
              <option value="aggressive">aggressive</option>
            </select>
          </div>
          <div>
            <label className="label">Budget tokens</label>
            <input className="input" type="number" value={form.budget_tokens}
                   onChange={(e) => set("budget_tokens", e.target.value)} placeholder="∞" />
          </div>
          <div>
            <label className="label">Budget turns</label>
            <input className="input" type="number" value={form.budget_turns}
                   onChange={(e) => set("budget_turns", e.target.value)} placeholder="∞" />
          </div>
        </div>

        {error && <p className="text-sm text-nzoyi-danger">{error}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" className="btn-ghost" onClick={() => router.back()}>Annuler</button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Lancement…" : "Lancer l'audit"}
          </button>
        </div>
      </form>
    </div>
  );
}
