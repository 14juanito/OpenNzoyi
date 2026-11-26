export function Header() {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-nzoyi-border bg-white px-6 py-3.5">
      <div className="flex items-center gap-2">
        <img src="/openzoyi-wordmark.png" alt="OpenZoyi" className="h-7" />
      </div>
      <div className="relative hidden flex-1 max-w-md md:block">
        <input className="input pl-9" placeholder="Rechercher une tâche, un actif, un finding…" />
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
             className="absolute left-3 top-2.5 h-4 w-4 text-nzoyi-slate">
          <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.3-4.3" strokeLinecap="round" />
        </svg>
      </div>
      <div className="flex items-center gap-3">
        <button className="relative flex h-9 w-9 items-center justify-center rounded-full border border-nzoyi-border text-nzoyi-slate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="h-4 w-4">
            <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"
                  strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-nzoyi-orange" />
        </button>
        <div className="flex items-center gap-2 rounded-full border border-nzoyi-border py-1 pl-1 pr-3">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-nzoyi-ink text-xs font-semibold text-white">
            NZ
          </span>
          <span className="hidden text-sm font-medium sm:block">Opérateur</span>
        </div>
      </div>
    </header>
  );
}
