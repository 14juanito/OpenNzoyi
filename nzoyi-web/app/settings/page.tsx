"use client";

import { useEffect, useState } from "react";
import { api, Secret, InterceptionRule } from "@/lib/api";

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Paramètres</h1>
        <p className="text-sm text-nzoyi-slate">Secrets chiffrés et règles d'interception</p>
      </div>
      <SecretsSection />
      <RulesSection />
    </div>
  );
}

function SecretsSection() {
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const load = () => api.listSecrets().then(setSecrets).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add() {
    if (!name.trim() || !value.trim()) return;
    await api.setSecret(name.trim(), value).catch(() => {});
    setName(""); setValue(""); load();
  }

  return (
    <div className="card">
      <h2 className="mb-1 font-semibold">Secrets (AES-256-GCM)</h2>
      <p className="mb-4 text-sm text-nzoyi-slate">
        Clés LLM, proxies, identifiants — chiffrés au repos. Les valeurs ne sont
        jamais réaffichées.
      </p>
      <div className="mb-4 flex flex-wrap gap-2">
        <input className="input max-w-[200px]" placeholder="NOM (ex. ANTHROPIC_API_KEY)"
               value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input max-w-[220px]" type="password" placeholder="valeur"
               value={value} onChange={(e) => setValue(e.target.value)} />
        <button className="btn-primary" onClick={add}>Ajouter</button>
      </div>
      {secrets.length === 0 ? (
        <p className="text-sm text-nzoyi-slate">Aucun secret.</p>
      ) : (
        <ul className="divide-y divide-nzoyi-border/60">
          {secrets.map((s) => (
            <li key={s.name} className="flex items-center justify-between py-2.5 text-sm">
              <span className="font-mono">{s.name} <span className="text-nzoyi-slate">••••••</span></span>
              <button onClick={() => api.deleteSecret(s.name).then(load)}
                      className="text-xs text-nzoyi-danger hover:underline">Supprimer</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RulesSection() {
  const [rules, setRules] = useState<InterceptionRule[]>([]);
  const [type, setType] = useState("string");
  const [pattern, setPattern] = useState("");
  const [action, setAction] = useState("deny");
  const load = () => api.listRules().then(setRules).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add() {
    if (!pattern.trim()) return;
    await api.addRule(type, pattern.trim(), action).catch(() => {});
    setPattern(""); load();
  }

  const ACTION_CLS: Record<string, string> = {
    deny: "text-nzoyi-danger", approve: "text-nzoyi-success", require_human: "text-nzoyi-amber",
  };

  return (
    <div className="card">
      <h2 className="mb-1 font-semibold">Règles d'interception</h2>
      <p className="mb-4 text-sm text-nzoyi-slate">
        Forcer approve / deny / require_human pour les commandes correspondant à
        une chaîne, une regex ou un préfixe argv.
      </p>
      <div className="mb-4 flex flex-wrap gap-2">
        <select className="input max-w-[150px]" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="string">string</option>
          <option value="regex">regex</option>
          <option value="argv_prefix">argv_prefix</option>
        </select>
        <input className="input max-w-[240px] font-mono" placeholder="motif (ex. --dump)"
               value={pattern} onChange={(e) => setPattern(e.target.value)} />
        <select className="input max-w-[150px]" value={action} onChange={(e) => setAction(e.target.value)}>
          <option value="deny">deny</option>
          <option value="approve">approve</option>
          <option value="require_human">require_human</option>
        </select>
        <button className="btn-primary" onClick={add}>Ajouter</button>
      </div>
      {rules.length === 0 ? (
        <p className="text-sm text-nzoyi-slate">Aucune règle — comportement par défaut (mode autonome).</p>
      ) : (
        <ul className="divide-y divide-nzoyi-border/60">
          {rules.map((r) => (
            <li key={r.id} className="flex items-center justify-between py-2.5 text-sm">
              <span className="font-mono text-xs">
                <span className="rounded bg-nzoyi-ink/5 px-1.5 py-0.5">{r.rule_type}</span>{" "}
                {Array.isArray(r.pattern) ? r.pattern.join(" ") : r.pattern}{" "}
                → <span className={ACTION_CLS[r.action]}>{r.action}</span>
              </span>
              <button onClick={() => api.deleteRule(r.id).then(load)}
                      className="text-xs text-nzoyi-danger hover:underline">Supprimer</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
