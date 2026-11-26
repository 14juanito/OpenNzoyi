export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Paramètres</h1>
        <p className="text-sm text-nzoyi-slate">Configuration de la plateforme</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h2 className="mb-2 font-semibold">Profils LLM</h2>
          <p className="text-sm text-nzoyi-slate">
            Fournisseur, clés (chiffrées), test de connexion. Couche stratégique
            uniquement — jamais dans la boucle d'évasion RL.
          </p>
        </div>
        <div className="card">
          <h2 className="mb-2 font-semibold">Sécurité</h2>
          <p className="text-sm text-nzoyi-slate">
            Règles d'interception, scope global, mode autonome / semi-autonome.
          </p>
        </div>
      </div>
    </div>
  );
}
