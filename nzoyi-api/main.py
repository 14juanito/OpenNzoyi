"""NZOYI audit CLI (Phase 2).

End-to-end loop: target → recon/vuln/ad_enum via Planner+Dispatcher+RL →
findings → JSON report. Tools that are not installed are skipped gracefully,
so the loop and the report are produced on any host; real findings require the
binaries and the authorised lab.

Usage:
    python main.py --target 192.168.100.11 --scope 192.168.100.0/24
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime

from engine import Engine
from report import write_report


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NZOYI — audit autonome (Phase 2)")
    p.add_argument("--target", required=True, help="IP ou domaine cible")
    p.add_argument(
        "--scope", action="append", default=[],
        help="CIDR ou domaine autorisé (répétable). Défaut: /32 de la cible.",
    )
    p.add_argument("--name", default="audit")
    p.add_argument("--profile", default="balanced",
                   choices=["quiet", "balanced", "aggressive"])
    p.add_argument("--out", default=None, help="chemin du rapport JSON")
    p.add_argument("--max-rounds", type=int, default=8)
    return p.parse_args()


async def _amain() -> int:
    args = _parse_args()
    scope = {"cidrs": [], "domains": []}
    for s in args.scope or [f"{args.target}/32"]:
        (scope["cidrs"] if "/" in s or s[0].isdigit() else scope["domains"]).append(s)

    engine = Engine()
    result = await engine.run(
        target=args.target, scope=scope, name=args.name,
        profile=args.profile, max_rounds=args.max_rounds,
    )

    os.makedirs("results", exist_ok=True)
    out = args.out or f"results/report_{datetime.now():%Y%m%d_%H%M%S}.json"
    write_report(result.report(), out)

    rep = result.report()
    print(f"[+] Cible      : {args.target}")
    print(f"[+] Actifs     : {rep['summary']['assets']}")
    print(f"[+] Findings   : {rep['summary']['findings_total']} "
          f"{rep['summary']['findings_by_severity']}")
    ran = sum(1 for o in result.outcomes if o.ran)
    skipped = [o.tool for o in result.outcomes if not o.ran]
    print(f"[+] Étapes     : {len(result.outcomes)} ({ran} exécutées)")
    if skipped:
        print(f"[~] Non exécutées (binaires absents): {', '.join(sorted(set(skipped)))}")
    print(f"[+] Rapport    : {out}")
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
