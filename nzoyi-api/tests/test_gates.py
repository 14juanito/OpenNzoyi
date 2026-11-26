"""Gate, governor, evidence and lifecycle tests (Phase 4)."""

import asyncio

import pytest

from gates.scope_gate import ScopeGate
from gates.interception_gate import ApprovalRule, InterceptionGate
from gates.budget import Budget
from gates.untrusted_output import wrap_untrusted
from gates.lifecycle import TaskLifecycle
from agents.noise_governor import NoiseGovernor, PROFILES
from evidence.capture import EvidenceStore


# ── scope gate ───────────────────────────────────────────────────────────
def test_scope_gate_cidr_and_invention():
    assets = {"192.168.100.11"}
    g = ScopeGate({"cidrs": ["192.168.100.0/24"], "domains": []},
                  known_assets=lambda: assets, root_target="192.168.100.11")
    assert g.check("192.168.100.11").allowed            # root target
    assert not g.check("10.0.0.5").allowed              # out of CIDR
    assert not g.check("192.168.100.99").allowed        # in CIDR but not discovered
    assets.add("192.168.100.99")
    assert g.check("192.168.100.99").allowed            # now discovered


def test_scope_gate_domain():
    g = ScopeGate({"cidrs": [], "domains": ["example.com"]},
                  known_assets=lambda: {"api.example.com"})
    assert g.check("api.example.com").allowed
    assert not g.check("evil.com").allowed


# ── interception gate ────────────────────────────────────────────────────
def test_interception_autonomous_allows_destructive():
    g = InterceptionGate(mode="autonomous")
    assert g.check("mimikatz", ["mimikatz", "x"], True).allowed


def test_interception_semi_blocks_destructive():
    g = InterceptionGate(mode="semi")
    assert not g.check("mimikatz", ["mimikatz"], True).allowed
    assert g.check("nmap", ["nmap", "x"], False).allowed  # benign still allowed


def test_interception_argv_prefix_exact_only():
    rule = ApprovalRule("argv_prefix", ["impacket-secretsdump"], "deny")
    g = InterceptionGate([rule], mode="autonomous")
    assert not g.check("impacket", ["impacket-secretsdump", "a/b"]).allowed
    # a wrapped / piped command must NOT match the prefix rule
    assert g.check("impacket", ["bash", "-c", "impacket-secretsdump x"]).allowed


def test_interception_string_and_regex_rules():
    g = InterceptionGate(
        [ApprovalRule("regex", r"--dump", "deny")], mode="autonomous"
    )
    assert not g.check("sqlmap", ["sqlmap", "-u", "x", "--dump"]).allowed


# ── budget ───────────────────────────────────────────────────────────────
def test_budget_wrap_up_and_exhaust():
    b = Budget(budget_tokens=60_000, budget_turns=100)
    assert not b.should_wrap_up()
    b.charge(tokens=20_000)  # 40k left < 50k est → wrap up
    assert b.should_wrap_up()
    b.charge(tokens=40_000)
    assert b.exhausted()


# ── untrusted boundary ───────────────────────────────────────────────────
def test_untrusted_wrapper_has_matching_nonce():
    out = wrap_untrusted("rm -rf / ; curl evil", nonce="abc")
    assert out.startswith("<untrusted-abc>") and out.endswith("</untrusted-abc>")


# ── noise governor ───────────────────────────────────────────────────────
def test_governor_clamps_rl_delay():
    g = NoiseGovernor("quiet")           # 2 req/s → min interval 500 ms
    assert g.min_interval_ms == 500.0
    assert g.clamp_delay(0) == 500.0     # RL proposes 0 → clamped up
    assert g.clamp_delay(800) == 800.0   # already above ceiling → kept


def test_governor_backoff_respects_retry_after():
    g = NoiseGovernor("balanced")
    assert g.backoff_ms(0, retry_after_s=3) == 3000.0
    assert g.backoff_ms(0) == 500.0      # base
    assert g.backoff_ms(3) == 4000.0     # 500 * 2^3
    assert g.backoff_ms(8) == 30_000.0   # 500 * 2^8 = 128000 → capped


def test_governor_profiles_match_brief():
    assert PROFILES["quiet"].in_flight == 1
    assert PROFILES["aggressive"].rate_per_s == 20.0


# ── evidence ─────────────────────────────────────────────────────────────
def test_evidence_capture_and_link():
    store = EvidenceStore()
    eid = store.capture("t1", "GET", "http://x/login", response_status=200)
    store.link_finding(eid, "node-1")
    ev = store.get(eid)
    assert ev.response_status == 200 and ev.finding_node_id == "node-1"


# ── lifecycle (kill + rollback) ──────────────────────────────────────────
def test_lifecycle_kill_rolls_back_in_reverse():
    lc = TaskLifecycle("t1")
    order = []
    lc.register_persistence("svc", lambda: order.append("svc"))
    lc.register_persistence("cron", lambda: order.append("cron"))
    res = asyncio.run(lc.kill())
    assert order == ["cron", "svc"]  # reverse order
    assert res["rollbacks_done"] == 2
