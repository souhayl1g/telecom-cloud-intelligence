-- 003_actuation_layer.sql — Real actuation primitives for L4 ADN agent
-- Adds: tickets, notifications_sent, churn_interventions, capacity_reports, retrain_runs
-- All tables idempotent (CREATE IF NOT EXISTS). Safe to run multiple times.
-- See docs/CHANGELOG.md "2026-05-19 — Actuation Layer" for full context.

-- ───────────────────────────────────────────────────────────────
-- Tickets (internal — no external ticketing dependency)
-- ───────────────────────────────────────────────────────────────
CREATE SEQUENCE IF NOT EXISTS tickets_seq START 1;

CREATE TABLE IF NOT EXISTS tickets (
  id                BIGSERIAL PRIMARY KEY,
  ticket_id         TEXT NOT NULL UNIQUE,           -- e.g. TT-2026-00042
  title             TEXT NOT NULL,
  description       TEXT,
  severity          TEXT NOT NULL,                  -- 'critical' | 'warning' | 'info'
  status            TEXT NOT NULL DEFAULT 'open',   -- 'open' | 'in_progress' | 'resolved' | 'closed'
  source_action_id  TEXT REFERENCES agent_actions(action_id) ON DELETE SET NULL,
  cell_id           TEXT,
  area              TEXT,
  assigned_to       TEXT,
  metadata          JSONB,                          -- anomaly snapshot, KPIs, Granger refs
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_area ON tickets(area);
CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at DESC);

-- ───────────────────────────────────────────────────────────────
-- Notifications audit (every SMS/email logged)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications_sent (
  id                BIGSERIAL PRIMARY KEY,
  channel           TEXT NOT NULL,                  -- 'sms' | 'email' | 'console'
  recipient         TEXT NOT NULL,                  -- imsi_hash, phone, or email
  subject           TEXT,
  body              TEXT NOT NULL,
  provider          TEXT,                           -- 'twilio' | 'smtp' | 'console'
  provider_msg_id   TEXT,
  status            TEXT NOT NULL,                  -- 'sent' | 'failed' | 'logged'
  error             TEXT,
  source_action_id  TEXT REFERENCES agent_actions(action_id) ON DELETE SET NULL,
  source_imsi_hash  TEXT,
  sent_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notif_recipient ON notifications_sent(recipient);
CREATE INDEX IF NOT EXISTS idx_notif_source_imsi ON notifications_sent(source_imsi_hash);
CREATE INDEX IF NOT EXISTS idx_notif_sent_at ON notifications_sent(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_notif_channel ON notifications_sent(channel);

-- ───────────────────────────────────────────────────────────────
-- Churn interventions (longitudinal outcome tracking)
-- Filled at creation by pb-churn-prevention playbook.
-- follow_up_cem + outcome filled by pipeline-worker intervention_tracker.
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS churn_interventions (
  id                       BIGSERIAL PRIMARY KEY,
  intervention_id          TEXT NOT NULL UNIQUE,
  imsi_hash                TEXT NOT NULL,
  intervention_type        TEXT NOT NULL,           -- 'sms_offer' | 'sim_upgrade_offer' | 'plan_upgrade' | 'ticket_created'
  cem_at_intervention      DOUBLE PRECISION,
  rat_gap_at_intervention  DOUBLE PRECISION,
  intervention_payload     JSONB,
  source_action_id         TEXT REFERENCES agent_actions(action_id) ON DELETE SET NULL,
  follow_up_cem            DOUBLE PRECISION,
  follow_up_checked_at     TIMESTAMPTZ,
  outcome                  TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'improved' | 'no_change' | 'worsened'
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_churn_int_imsi ON churn_interventions(imsi_hash);
CREATE INDEX IF NOT EXISTS idx_churn_int_outcome ON churn_interventions(outcome);
CREATE INDEX IF NOT EXISTS idx_churn_int_created ON churn_interventions(created_at DESC);

-- ───────────────────────────────────────────────────────────────
-- Capacity reports registry (PDF artifacts in MinIO)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS capacity_reports (
  id                BIGSERIAL PRIMARY KEY,
  report_id         TEXT NOT NULL UNIQUE,
  area              TEXT,
  report_type       TEXT NOT NULL DEFAULT 'capacity_recommendation',
  minio_key         TEXT NOT NULL,                  -- reports/YYYY-MM-DD/<report_id>.pdf
  presigned_url     TEXT,
  url_expires_at    TIMESTAMPTZ,
  metrics_summary   JSONB,
  source_action_id  TEXT REFERENCES agent_actions(action_id) ON DELETE SET NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reports_area ON capacity_reports(area);
CREATE INDEX IF NOT EXISTS idx_reports_created ON capacity_reports(created_at DESC);

-- ───────────────────────────────────────────────────────────────
-- Retrain runs registry (audit trail for pb-retrain-model)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS retrain_runs (
  id                BIGSERIAL PRIMARY KEY,
  run_id            TEXT NOT NULL UNIQUE,
  model_name        TEXT NOT NULL,                  -- 'cem' | 'rat' | 'vae'
  notebook_path     TEXT NOT NULL,
  output_path       TEXT,                           -- executed .ipynb in MinIO
  status            TEXT NOT NULL,                  -- 'started' | 'succeeded' | 'failed'
  started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at       TIMESTAMPTZ,
  metrics_before    JSONB,
  metrics_after     JSONB,
  source_action_id  TEXT REFERENCES agent_actions(action_id) ON DELETE SET NULL,
  error             TEXT
);

CREATE INDEX IF NOT EXISTS idx_retrain_model ON retrain_runs(model_name);
CREATE INDEX IF NOT EXISTS idx_retrain_status ON retrain_runs(status);
CREATE INDEX IF NOT EXISTS idx_retrain_started ON retrain_runs(started_at DESC);
