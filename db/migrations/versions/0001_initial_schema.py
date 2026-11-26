"""Initial NZOYI schema (mission brief, section 3).

Creates the 13 core tables of the autonomous auditor: tasks, assets, nodes,
edges, anchors, todolist, agent_runs, evidence, findings, q_tables,
approval_rules, approvals, secrets. Postgres-native (UUID, JSONB, BYTEA,
gen_random_uuid, CHECK constraints).

Revision ID: 0001
Revises:
Create Date: 2026-11-26
"""
from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # gen_random_uuid() is in core since PG13; pgcrypto kept for portability.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.execute(
        """
        CREATE TABLE tasks (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          target TEXT NOT NULL,
          scope JSONB NOT NULL,
          profile TEXT DEFAULT 'balanced'
            CHECK (profile IN ('quiet','balanced','aggressive')),
          llm_profile_id UUID,
          status TEXT DEFAULT 'pending'
            CHECK (status IN ('pending','running','paused','done','failed')),
          budget_tokens INT,
          budget_turns INT,
          created_at TIMESTAMPTZ DEFAULT now(),
          updated_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE assets (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID,
          type TEXT NOT NULL
            CHECK (type IN ('domain','subdomain','ip','service','endpoint')),
          value TEXT NOT NULL,
          parent_id UUID REFERENCES assets(id),
          dedup_key TEXT UNIQUE NOT NULL,
          metadata JSONB DEFAULT '{}',
          discovered_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_assets_company_id ON assets(company_id);")
    op.execute("CREATE INDEX ix_assets_parent_id ON assets(parent_id);")

    op.execute(
        """
        CREATE TABLE nodes (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
          type TEXT NOT NULL
            CHECK (type IN ('goal','intent','fact','finding','hint')),
          content JSONB NOT NULL,
          status TEXT DEFAULT 'open',
          agent TEXT,
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_nodes_task_id ON nodes(task_id);")
    op.execute("CREATE INDEX ix_nodes_task_type ON nodes(task_id, type);")

    op.execute(
        """
        CREATE TABLE edges (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          source_id UUID REFERENCES nodes(id) ON DELETE CASCADE,
          target_id UUID REFERENCES nodes(id) ON DELETE CASCADE,
          relation TEXT NOT NULL
            CHECK (relation IN ('spawns','derived_from','yields','proves'))
        );
        """
    )
    op.execute("CREATE INDEX ix_edges_source_id ON edges(source_id);")
    op.execute("CREATE INDEX ix_edges_target_id ON edges(target_id);")

    op.execute(
        """
        CREATE TABLE anchors (
          node_id UUID REFERENCES nodes(id) ON DELETE CASCADE,
          asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
          PRIMARY KEY (node_id, asset_id)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE todolist (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
          step_order INT NOT NULL,
          action TEXT NOT NULL,
          prerequisites JSONB NOT NULL,
          status TEXT DEFAULT 'blocked'
            CHECK (status IN ('blocked','ready','running','done','failed')),
          intent_node_id UUID REFERENCES nodes(id)
        );
        """
    )
    op.execute("CREATE INDEX ix_todolist_task_order ON todolist(task_id, step_order);")

    op.execute(
        """
        CREATE TABLE agent_runs (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
          intent_node_id UUID REFERENCES nodes(id),
          agent TEXT NOT NULL,
          tool TEXT,
          tokens_used INT DEFAULT 0,
          turns_used INT DEFAULT 0,
          started_at TIMESTAMPTZ DEFAULT now(),
          ended_at TIMESTAMPTZ
        );
        """
    )
    op.execute("CREATE INDEX ix_agent_runs_task_id ON agent_runs(task_id);")

    op.execute(
        """
        CREATE TABLE evidence (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
          finding_node_id UUID REFERENCES nodes(id),
          request_method TEXT,
          request_url TEXT,
          request_headers JSONB,
          request_body BYTEA,
          response_status INT,
          response_headers JSONB,
          response_body BYTEA,
          captured_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_evidence_task_id ON evidence(task_id);")

    op.execute(
        """
        CREATE TABLE findings (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
          node_id UUID REFERENCES nodes(id),
          asset_id UUID REFERENCES assets(id),
          title TEXT NOT NULL,
          severity TEXT CHECK (severity IN ('info','low','medium','high','critical')),
          status TEXT DEFAULT 'unverified'
            CHECK (status IN ('unverified','verified','fixed','false_positive')),
          evidence_id UUID REFERENCES evidence(id),
          retest_status TEXT,
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_findings_task_id ON findings(task_id);")
    op.execute("CREATE INDEX ix_findings_severity ON findings(severity);")

    op.execute(
        """
        CREATE TABLE q_tables (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
          phase TEXT NOT NULL,
          state_hash TEXT NOT NULL,
          action_hash TEXT NOT NULL,
          q_value DOUBLE PRECISION NOT NULL,
          updated_at TIMESTAMPTZ DEFAULT now(),
          UNIQUE(task_id, phase, state_hash, action_hash)
        );
        """
    )
    op.execute("CREATE INDEX ix_q_tables_task_phase ON q_tables(task_id, phase);")

    op.execute(
        """
        CREATE TABLE approval_rules (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
          rule_type TEXT CHECK (rule_type IN ('string','regex','argv_prefix')),
          pattern TEXT NOT NULL,
          action TEXT CHECK (action IN ('approve','deny','require_human')),
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_approval_rules_task_id ON approval_rules(task_id);")

    op.execute(
        """
        CREATE TABLE approvals (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
          agent_run_id UUID REFERENCES agent_runs(id),
          tool_call JSONB NOT NULL,
          status TEXT DEFAULT 'pending'
            CHECK (status IN ('pending','approved','denied')),
          decided_by TEXT CHECK (decided_by IN ('human','rule','model','system')),
          decided_at TIMESTAMPTZ
        );
        """
    )
    op.execute("CREATE INDEX ix_approvals_task_status ON approvals(task_id, status);")

    op.execute(
        """
        CREATE TABLE secrets (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT UNIQUE NOT NULL,
          value_encrypted BYTEA NOT NULL,
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    for table in (
        "secrets",
        "approvals",
        "approval_rules",
        "q_tables",
        "findings",
        "evidence",
        "agent_runs",
        "todolist",
        "anchors",
        "edges",
        "nodes",
        "assets",
        "tasks",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
