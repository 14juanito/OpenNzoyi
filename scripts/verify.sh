#!/usr/bin/env bash
# NZOYI — CI locale (Phase 1).
#
# Garde-fous non négociables vérifiés à chaque phase :
#   1. Les 72 tests de validation d'origine passent (non-régression).
#   2. Aucune référence à la couche LLM dans nzoyi-core/evasion/ (boucle
#      d'évasion = RL pur, contrainte d'architecture).
#   3. Le microservice RL s'importe et répond (smoke, backend mémoire).
#
# Usage : bash scripts/verify.sh
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
fail=0

echo "──────────────────────────────────────────────────────────────"
echo "[1/3] pytest tests/test_validation.py (attendu : 72 passed)"
echo "──────────────────────────────────────────────────────────────"
if python3 -m pytest tests/test_validation.py -q 2>&1 | tail -3; then
  :
fi
# Re-run capturing the summary line for a hard check.
summary="$(python3 -m pytest tests/test_validation.py -q 2>&1 | grep -E '[0-9]+ passed' | tail -1)"
if echo "$summary" | grep -qE '72 passed' && ! echo "$summary" | grep -qE 'failed'; then
  echo "  OK : $summary"
else
  echo "  ECHEC : $summary"
  fail=1
fi

echo
echo "──────────────────────────────────────────────────────────────"
echo "[2/3] Gate LLM : grep dans nzoyi-core/evasion/ (attendu : 0)"
echo "──────────────────────────────────────────────────────────────"
# Naive gate (brief) + import gate, sur les sources .py uniquement.
hits="$(grep -rniE 'llm|anthropic|openai|from +nzoyi\.llm|import +nzoyi\.llm' \
        "$ROOT/nzoyi-core/evasion/" --include='*.py' 2>/dev/null || true)"
if [ -z "$hits" ]; then
  echo "  OK : 0 référence LLM dans nzoyi-core/evasion/*.py"
else
  echo "  ECHEC : références LLM trouvées :"
  echo "$hits"
  fail=1
fi

echo
echo "──────────────────────────────────────────────────────────────"
echo "[3/3] Smoke microservice RL (TestClient, backend mémoire)"
echo "──────────────────────────────────────────────────────────────"
if NZOYI_RL_SEED=1 python3 - <<'PY'
import os, sys
os.environ.pop("NZOYI_DATABASE_URL", None)  # force in-memory for the smoke
os.environ.pop("DATABASE_URL", None)
sys.path.insert(0, "nzoyi-core")
from fastapi.testclient import TestClient
import api
c = TestClient(api.app)
h = c.get("/health").json()
assert h["status"] == "ok" and h["state_space_size"] == 1512 and h["llm_in_loop"] is False, h
st = {"target_os":"linux","open_ports_bucket":"0-3","privilege_level":"user",
      "alert_count_5min":"0","sdn_flow_blocks":"0","phase":"recon"}
na = c.post("/evasion/next_action", json={"task_id":"ci","state":st,"phase":"recon"}).json()
assert na["tool"] in ("nmap","rustscan","httpx","subfinder"), na
nxt = dict(st); nxt["phase"] = "vuln"
u = c.post("/evasion/update", json={"task_id":"ci","state":st,
     "action_hash":na["action_hash"],"reward":1.0,"next_state":nxt}).json()
assert abs(u["q_value"] - 0.1) < 1e-9, u  # alpha*reward = 0.1*1.0
print("  OK : health + next_action + update (q=%.3f)" % u["q_value"])
PY
then :; else echo "  ECHEC : smoke RL"; fail=1; fi

echo
if [ "$fail" -eq 0 ]; then
  echo "VERIFY: TOUT VERT [OK]"
else
  echo "VERIFY: ECHEC [FAIL]"
fi
exit "$fail"
