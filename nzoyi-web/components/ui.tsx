import { ReactNode } from "react";

const SEV: Record<string, string> = {
  critical: "bg-nzoyi-danger/10 text-nzoyi-danger",
  high: "bg-nzoyi-orange/10 text-nzoyi-orange",
  medium: "bg-nzoyi-amber/10 text-nzoyi-amber",
  low: "bg-nzoyi-slate/10 text-nzoyi-slate",
  info: "bg-nzoyi-ink/5 text-nzoyi-slate",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`badge ${SEV[severity] ?? SEV.info}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {severity}
    </span>
  );
}

const STATUS: Record<string, string> = {
  running: "text-nzoyi-orange",
  done: "text-nzoyi-success",
  failed: "text-nzoyi-danger",
  killed: "text-nzoyi-danger",
  pending: "text-nzoyi-slate",
  paused: "text-nzoyi-slate",
};

export function StatusDot({ status }: { status: string }) {
  return (
    <span className={`badge ${STATUS[status] ?? "text-nzoyi-slate"}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  );
}

export function StatCard({
  label, value, hint, accent, children,
}: {
  label: string; value: ReactNode; hint?: ReactNode; accent?: boolean; children?: ReactNode;
}) {
  return (
    <div className={`card ${accent ? "bg-nzoyi-orange text-white border-nzoyi-orange" : ""}`}>
      <p className={`text-sm ${accent ? "text-white/80" : "text-nzoyi-slate"}`}>{label}</p>
      <p className="mt-2 text-3xl font-bold tracking-tight">{value}</p>
      {hint && <p className={`mt-1 text-xs ${accent ? "text-white/80" : "text-nzoyi-slate"}`}>{hint}</p>}
      {children}
    </div>
  );
}
