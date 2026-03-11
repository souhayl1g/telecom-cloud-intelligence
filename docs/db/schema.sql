-- Telecom Cloud Intelligence Platform — PostgreSQL Schema
-- Reflects the deployed database structure (serial bigint PKs, run_id text FK)
-- Apply manually: psql -U telecom -d telecom_intel -f schema.sql

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

CREATE TABLE IF NOT EXISTS model_registry (
  id                  BIGSERIAL PRIMARY KEY,
  model_name          TEXT NOT NULL,
  version             TEXT NOT NULL,
  artifact_object_key TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(model_name, version)
);

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

CREATE TABLE IF NOT EXISTS revenue_anomalies (
  id             BIGSERIAL PRIMARY KEY,
  run_id         TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
  ts             TIMESTAMPTZ,
  region         TEXT,
  operator       TEXT,
  subscriber_id  TEXT,
  line_type      TEXT,              -- 'prepaid' | 'postpaid'
  plan           TEXT,
  metric_name    TEXT NOT NULL DEFAULT 'composite_bss',
  severity       DOUBLE PRECISION,
  value          DOUBLE PRECISION,
  baseline_value DOUBLE PRECISION,
  model_name     TEXT NOT NULL DEFAULT 'revenue-anomaly',
  model_version  TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
