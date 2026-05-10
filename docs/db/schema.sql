-- Telecom NeXoligence Platform — PostgreSQL Schema
-- Reflects the deployed database structure (serial bigint PKs, run_id text FK)
-- Apply manually: psql -U telecom -d telecom_intel -f schema.sql

-- ───────────────────────────────────────────────────────────────
-- Authentication & Users
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT,                    -- NULL for OAuth-only users
    full_name     TEXT,
    avatar_url    TEXT,
    provider      TEXT NOT NULL DEFAULT 'local',  -- 'local' | 'google' | 'github'
    provider_id   TEXT,                    -- OAuth provider's user ID
    role          TEXT NOT NULL DEFAULT 'viewer',  -- 'viewer' | 'analyst' | 'admin'
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(provider, provider_id)
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id);

-- ───────────────────────────────────────────────────────────────
-- Pipeline & Analytics
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id            BIGSERIAL PRIMARY KEY,
  run_id        TEXT NOT NULL UNIQUE,
  status        TEXT NOT NULL DEFAULT 'started',
  started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at   TIMESTAMPTZ,
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS dataset_registry (
  id             BIGSERIAL PRIMARY KEY,
  run_id         TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  dataset_type   TEXT NOT NULL,          -- 'oss' | 'bss' | 'curated'
  layer          TEXT NOT NULL,          -- 'raw' | 'processed' | 'curated'
  format         TEXT NOT NULL DEFAULT 'json',
  object_key     TEXT NOT NULL,
  schema_version TEXT NOT NULL DEFAULT 'v1',
  row_count      BIGINT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- model_registry table dropped in migration 002 (unused — see ai-service/model_cache).

CREATE TABLE IF NOT EXISTS anomalies (
  id             BIGSERIAL PRIMARY KEY,
  run_id         TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  ts             TIMESTAMPTZ,
  region         TEXT,
  cell_id        TEXT,
  kpi_name       TEXT NOT NULL,
  severity       DOUBLE PRECISION,
  value          DOUBLE PRECISION,
  baseline_value DOUBLE PRECISION,
  model_name     TEXT NOT NULL DEFAULT 'anomaly',
  model_version  TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sla_risk_scores (
  id            BIGSERIAL PRIMARY KEY,
  run_id        TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  region        TEXT,
  window_start  TIMESTAMPTZ,
  window_end    TIMESTAMPTZ,
  score         DOUBLE PRECISION NOT NULL CHECK (score >= 0 AND score <= 1),
  explanation   JSONB,
  model_name    TEXT NOT NULL DEFAULT 'sla-risk',
  model_version TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS correlation_insights (
  id           BIGSERIAL PRIMARY KEY,
  run_id       TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  region       TEXT,
  metric_x     TEXT NOT NULL,
  metric_y     TEXT NOT NULL,
  window_start TIMESTAMPTZ,
  window_end   TIMESTAMPTZ,
  method       TEXT NOT NULL DEFAULT 'pearson',
  corr_value   DOUBLE PRECISION,
  p_value      DOUBLE PRECISION,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Renamed from revenue_anomalies (Migration 001). Analytic surface = CEM,
-- not revenue/billing. Subscriber-level CEM-impacting events.
CREATE TABLE IF NOT EXISTS cem_anomalies (
  id             BIGSERIAL PRIMARY KEY,
  run_id         TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  ts             TIMESTAMPTZ,
  region         TEXT,
  operator       TEXT,
  subscriber_id  TEXT,
  line_type      TEXT,              -- 'prepaid' | 'postpaid'
  plan           TEXT,
  metric_name    TEXT NOT NULL DEFAULT 'composite_cem',
  severity       DOUBLE PRECISION,
  value          DOUBLE PRECISION,
  baseline_value DOUBLE PRECISION,
  model_name     TEXT NOT NULL DEFAULT 'cem-anomaly',
  model_version  TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ───────────────────────────────────────────────────────────────
-- ADN L4 Agent Actions
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_actions (
  id            BIGSERIAL PRIMARY KEY,
  action_id     TEXT NOT NULL UNIQUE,
  type          TEXT NOT NULL,              -- 'auto_remediation','recommendation','prediction','escalation'
  title         TEXT NOT NULL,
  description   TEXT,
  severity      TEXT NOT NULL,              -- 'critical','warning','info'
  status        TEXT NOT NULL DEFAULT 'pending',  -- 'pending','approved','executed','rejected','auto_approved'
  source        TEXT,
  confidence    DOUBLE PRECISION,
  impact        TEXT,
  playbook_id   TEXT,
  execution_log JSONB,                      -- what the playbook actually did
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at   TIMESTAMPTZ,
  resolved_by   TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_actions_status ON agent_actions(status);
CREATE INDEX IF NOT EXISTS idx_agent_actions_created ON agent_actions(created_at DESC);

-- ───────────────────────────────────────────────────────────────
-- Phase 3.5: Real BSS Subscriber Data + Multi-Month Simulation
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bss_subscribers (
  id               BIGSERIAL PRIMARY KEY,
  imsi_hash        TEXT NOT NULL,           -- SHA-256 anonymized IMSI
  tac              TEXT,
  model            TEXT,
  brand            TEXT,
  tertype          TEXT,
  generation       TEXT,                    -- device max RAT capability
  sim_slot         TEXT,
  volte_flag       INTEGER,
  usim_flag        INTEGER,
  area             TEXT,
  area_delegation  TEXT,
  usertype         TEXT,
  dou_total        BIGINT,                  -- bytes
  traffic_2g       BIGINT,
  traffic_3g       BIGINT,
  traffic_4g       BIGINT,
  traffic_5g       BIGINT,
  duration         DOUBLE PRECISION,         -- voice seconds
  voice_onlinetime_3g DOUBLE PRECISION,
  voice_onlinetime_2g DOUBLE PRECISION,
  s1_mme_sr        DOUBLE PRECISION,
  iu_attach_sr     DOUBLE PRECISION,
  gb_attach_sr     DOUBLE PRECISION,
  session_flag     INTEGER,
  highest_rat      TEXT,
  month_year       TEXT NOT NULL,           -- e.g. '2026-02'
  churned          BOOLEAN DEFAULT FALSE,   -- LSTM churn ground-truth label
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(imsi_hash, month_year)
);

CREATE INDEX IF NOT EXISTS idx_bss_area ON bss_subscribers(area);
CREATE INDEX IF NOT EXISTS idx_bss_month ON bss_subscribers(month_year);
CREATE INDEX IF NOT EXISTS idx_bss_usertype ON bss_subscribers(usertype);
CREATE INDEX IF NOT EXISTS idx_bss_highest_rat ON bss_subscribers(highest_rat);

-- ───────────────────────────────────────────────────────────────
-- OSS Cell KPIs (Simulated, Area-Correlated)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS oss_cell_kpis (
  id               BIGSERIAL PRIMARY KEY,
  cell_id          TEXT NOT NULL,
  area             TEXT NOT NULL,
  month_year       TEXT NOT NULL,
  throughput_mbps  DOUBLE PRECISION,
  latency_ms       DOUBLE PRECISION,
  packet_loss_rate DOUBLE PRECISION,
  jitter_ms        DOUBLE PRECISION,
  active_users     INTEGER,
  rsrp_dbm         DOUBLE PRECISION,
  cell_load_pct    DOUBLE PRECISION,        -- 0-100
  anomaly_flag     BOOLEAN DEFAULT FALSE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_oss_cell_area ON oss_cell_kpis(area);
CREATE INDEX IF NOT EXISTS idx_oss_cell_month ON oss_cell_kpis(month_year);
CREATE INDEX IF NOT EXISTS idx_oss_cell_id ON oss_cell_kpis(cell_id);

-- ───────────────────────────────────────────────────────────────
-- Subscriber Derived Features / CEM Scores
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subscriber_features (
  id                    BIGSERIAL PRIMARY KEY,
  imsi_hash             TEXT NOT NULL,
  month_year            TEXT NOT NULL,
  rat_gap_score         DOUBLE PRECISION,  -- 0=matched, 1=severely underserved
  usim_bottleneck       BOOLEAN,           -- 4G device + 2G SIM
  data_intensity        DOUBLE PRECISION,  -- bytes per voice second
  network_experience_index DOUBLE PRECISION, -- weighted attach SRs
  cem_score             DOUBLE PRECISION,  -- 0-1, computed or predicted
  cem_score_target      DOUBLE PRECISION,  -- ground truth composite
  churn_risk_flag       BOOLEAN,
  churned               BOOLEAN DEFAULT FALSE,  -- ground-truth churn label
  features_json         JSONB,             -- extensible feature store
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(imsi_hash, month_year)
);

CREATE INDEX IF NOT EXISTS idx_sub_feat_imsi ON subscriber_features(imsi_hash);
CREATE INDEX IF NOT EXISTS idx_sub_feat_month ON subscriber_features(month_year);

-- ───────────────────────────────────────────────────────────────
-- Area-Level Network Health + CEM Aggregation
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS area_network_health (
  id                BIGSERIAL PRIMARY KEY,
  area              TEXT NOT NULL,
  month_year        TEXT NOT NULL,
  avg_throughput    DOUBLE PRECISION,
  avg_latency       DOUBLE PRECISION,
  avg_packet_loss   DOUBLE PRECISION,
  anomaly_count     INTEGER DEFAULT 0,
  subscriber_count  INTEGER,
  avg_cem_score     DOUBLE PRECISION,
  underserved_pct   DOUBLE PRECISION,      -- % with rat_gap_score > 0.5
  usim_bottleneck_pct DOUBLE PRECISION,
  health_json       JSONB,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(area, month_year)
);

CREATE INDEX IF NOT EXISTS idx_area_health_area ON area_network_health(area);
CREATE INDEX IF NOT EXISTS idx_area_health_month ON area_network_health(month_year);

-- ───────────────────────────────────────────────────────────────
-- Multi-Agent System: Conversations + Reasoning Logs
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_conversations (
  id            BIGSERIAL PRIMARY KEY,
  thread_id     TEXT NOT NULL UNIQUE,
  user_id       BIGINT REFERENCES users(id) ON DELETE SET NULL,
  title         TEXT,
  messages      JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conv_thread ON agent_conversations(thread_id);
CREATE INDEX IF NOT EXISTS idx_conv_user ON agent_conversations(user_id);

CREATE TABLE IF NOT EXISTS agent_reasoning_logs (
  id            BIGSERIAL PRIMARY KEY,
  thread_id     TEXT REFERENCES agent_conversations(thread_id) ON DELETE CASCADE,
  agent_name    TEXT NOT NULL,
  intent        TEXT,
  input_payload JSONB,
  output_payload JSONB,
  latency_ms    INTEGER,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reasoning_thread ON agent_reasoning_logs(thread_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_agent ON agent_reasoning_logs(agent_name);

-- ───────────────────────────────────────────────────────────────
-- v3.0 ML Inference Results
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cem_scores (
  id            BIGSERIAL PRIMARY KEY,
  run_id        TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  subscriber_id TEXT,
  region        TEXT,
  cem_score     DOUBLE PRECISION,
  model_name    TEXT NOT NULL DEFAULT 'cem',
  model_version TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cem_run ON cem_scores(run_id);

CREATE TABLE IF NOT EXISTS rat_underservice_scores (
  id               BIGSERIAL PRIMARY KEY,
  run_id           TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  subscriber_id    TEXT,
  region           TEXT,
  is_underserved   BOOLEAN,
  underservice_prob DOUBLE PRECISION,
  model_name       TEXT NOT NULL DEFAULT 'rat-underservice',
  model_version    TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rat_run ON rat_underservice_scores(run_id);

CREATE TABLE IF NOT EXISTS vae_anomaly_scores (
  id                  BIGSERIAL PRIMARY KEY,
  run_id              TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  ts                  TIMESTAMPTZ,
  region              TEXT,
  cell_id             TEXT,
  is_anomaly          BOOLEAN,
  anomaly_score       DOUBLE PRECISION,
  reconstruction_error DOUBLE PRECISION,
  model_name          TEXT NOT NULL DEFAULT 'vae-anomaly',
  model_version       TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vae_run ON vae_anomaly_scores(run_id);

-- ───────────────────────────────────────────────────────────────
-- Granger Causality Results
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS granger_causality_results (
  id            BIGSERIAL PRIMARY KEY,
  area          TEXT NOT NULL,
  oss_variable  TEXT NOT NULL,
  cem_variable  TEXT NOT NULL,        -- renamed from bss_variable (Migration 001)
  direction     TEXT NOT NULL,
  max_lag       INTEGER NOT NULL,
  best_lag      INTEGER,
  best_pvalue   DOUBLE PRECISION,
  best_fstat    DOUBLE PRECISION,
  significant   BOOLEAN DEFAULT FALSE,
  test_summary  JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (area, oss_variable, cem_variable, direction)
);

CREATE INDEX IF NOT EXISTS idx_granger_area ON granger_causality_results(area);
CREATE INDEX IF NOT EXISTS idx_granger_significant ON granger_causality_results(significant);

