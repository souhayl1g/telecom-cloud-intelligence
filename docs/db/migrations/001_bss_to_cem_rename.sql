-- Migration 001 — BSS → CEM analytic surface rename
-- Apply: psql -U telecom -d telecom_intel -f migrations/001_bss_to_cem_rename.sql
-- Idempotent: safe to re-run.
-- Scope: rename analytic-layer tables/columns from "BSS" to "CEM" (SmartCare-aligned).
--        Raw-load table bss_subscribers is preserved (it represents the data SOURCE,
--        not the analytic surface).

BEGIN;

-- ── 1. revenue_anomalies → cem_anomalies ───────────────────────────────────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'revenue_anomalies')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables
                       WHERE table_schema = 'public' AND table_name = 'cem_anomalies') THEN
        ALTER TABLE revenue_anomalies RENAME TO cem_anomalies;
    END IF;
END $$;

-- ── 2. cem_anomalies.model_name default revenue-anomaly → cem-anomaly ──────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'cem_anomalies') THEN
        EXECUTE 'ALTER TABLE cem_anomalies ALTER COLUMN model_name SET DEFAULT ''cem-anomaly''';
        UPDATE cem_anomalies SET model_name = 'cem-anomaly' WHERE model_name = 'revenue-anomaly';
    END IF;
END $$;

-- ── 3. granger_causality_results.bss_variable → cem_variable ───────────────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'public'
                 AND table_name = 'granger_causality_results'
                 AND column_name = 'bss_variable') THEN
        ALTER TABLE granger_causality_results RENAME COLUMN bss_variable TO cem_variable;
    END IF;
END $$;

-- ── 4. model_registry: revenue-anomaly → cem-anomaly ──────────────────────
UPDATE model_registry SET model_name = 'cem-anomaly' WHERE model_name = 'revenue-anomaly';

COMMIT;
