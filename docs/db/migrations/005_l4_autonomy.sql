-- 005_l4_autonomy.sql — L4 closed-loop autonomy envelope
-- Adds the guardrail config that turns the L3 (human-approved) agent into a
-- genuine L4 closed loop: the system executes inside a bounded envelope
-- (confidence threshold + playbook whitelist + hourly rate limit + kill-switch)
-- and marks every unattended decision for audit.
--
-- Idempotent: safe to re-run. Applied automatically by data-init on fresh DBs
-- (schema.sql mirrors this) and manually on existing DBs via:
--   docker compose exec -T postgres psql -U telecom -d telecom_intel -f - < docs/db/migrations/005_l4_autonomy.sql

-- 1. Single-row autonomy configuration (the "safety envelope").
CREATE TABLE IF NOT EXISTS agent_autonomy_config (
  id                  INT PRIMARY KEY DEFAULT 1,
  armed               BOOLEAN NOT NULL DEFAULT FALSE,        -- master switch: is closed-loop ON?
  confidence_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.85, -- min model confidence to act unattended
  playbook_whitelist  TEXT[] NOT NULL DEFAULT '{}',          -- ONLY these playbooks may self-execute
  max_actions_per_hour INT NOT NULL DEFAULT 10,              -- rate limit on autonomous executions
  kill_switch         BOOLEAN NOT NULL DEFAULT FALSE,        -- emergency stop for the autonomous path
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by          TEXT,
  CONSTRAINT agent_autonomy_config_singleton CHECK (id = 1)
);

-- Seed the single row with safe defaults (disarmed, empty whitelist => nothing runs).
INSERT INTO agent_autonomy_config (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- 2. Mark which actions were decided by the machine vs a human (audit trail).
ALTER TABLE agent_actions
  ADD COLUMN IF NOT EXISTS decided_by TEXT;   -- 'L4-autonomous' | NULL (human/manual)

-- Fast lookup for the hourly rate-limit window.
CREATE INDEX IF NOT EXISTS idx_agent_actions_decided_resolved
  ON agent_actions(decided_by, resolved_at DESC);
