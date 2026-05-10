-- Migration 002 — Drop unused model_registry table
-- Apply: psql -U telecom -d telecom_intel -f migrations/002_drop_model_registry.sql
-- Idempotent: safe to re-run.
-- Rationale: per CLAUDE.md junk audit, model_registry is populated by
-- pipeline-worker but never queried by any router or notebook.
-- Inference is served from disk-loaded artifacts via ai-service/model_cache,
-- so the table provides no value.

BEGIN;

DROP TABLE IF EXISTS model_registry CASCADE;

COMMIT;
