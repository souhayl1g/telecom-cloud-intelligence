-- ──────────────────────────────────────────────────────────────────────────
-- Migration 008 — Performance indexes for operational browsers
-- ──────────────────────────────────────────────────────────────────────────
-- The engineer browser pages (OSS Cells, BSS Subscribers) query large tables
-- with ORDER BY + LIMIT. Without matching indexes these become full-sort
-- operations on 18M+ rows. Two targeted composite indexes bring both queries
-- down to index-scan + early termination.
-- ──────────────────────────────────────────────────────────────────────────

BEGIN;

-- BSS subscriber browser: ORDER BY cem_score ASC LIMIT N
-- Without this, a full scan of ~2.4M subscriber_features rows is sorted.
-- With this, PG uses the index to walk the bottom of the score range first
-- and stops as soon as it has collected LIMIT rows.
CREATE INDEX IF NOT EXISTS idx_sub_feat_cem
    ON subscriber_features (cem_score ASC NULLS LAST);

-- OSS cell browser (via vw_oss_cell_derived): ORDER BY anomaly_flag DESC, timestamp DESC LIMIT N
-- PG sees through the view to this base-table index.
-- The partial idx_oss_cell_anomaly only covers WHERE anomaly_flag=TRUE;
-- this compound index handles the full ORDER BY without a filter.
CREATE INDEX IF NOT EXISTS idx_oss_cell_anomaly_ts
    ON oss_cell_kpis (anomaly_flag DESC NULLS LAST, timestamp DESC NULLS LAST);

COMMIT;
