-- ──────────────────────────────────────────────────────────────────────────
-- Migration 004 — Engineered KPI proxies on top of real Huawei OSS data
-- ──────────────────────────────────────────────────────────────────────────
-- Real Huawei OSS CSV exports contain:
--   2G: integrity, call_drop_rate
--   3G: integrity, call_drop_rate, throughput_mbps
--   4G: integrity, call_drop_rate, throughput_mbps, rsrp_dbm, active_users
--       AND L.Traffic.User.Max (currently dropped by ingest — captured now)
--
-- Latency, packet loss, jitter, cell load are NOT in source. This migration
-- adds:
--   1. active_users_max column     — real 4G data, captured from L.Traffic.User.Max
--   2. vw_oss_cell_derived view    — REAL columns + deterministic engineered
--                                     proxies (latency, loss, cell_load).
--
-- The proxy formulas are documented per 3GPP TR 38.913 / Huawei eRAN handbook
-- and applied at view-read time — never written into the table. The base
-- `oss_cell_kpis` table is never mutated by this migration.
-- ──────────────────────────────────────────────────────────────────────────

BEGIN;

-- ── 1. New REAL column for 4G max user count ────────────────────────────────
ALTER TABLE oss_cell_kpis
    ADD COLUMN IF NOT EXISTS active_users_max INTEGER;

COMMENT ON COLUMN oss_cell_kpis.active_users_max IS
    'Real: L.Traffic.User.Max from Huawei 4G OSS export. NULL for 2G/3G.';


-- ── 2. View with engineered KPI proxies ─────────────────────────────────────
DROP VIEW IF EXISTS vw_oss_cell_derived CASCADE;

CREATE VIEW vw_oss_cell_derived AS
SELECT
    id, cell_id, area, month_year, site_name, source, rat_type, timestamp, created_at,

    -- Real Huawei measurements
    integrity,
    call_drop_rate,
    throughput_mbps,
    active_users,
    active_users_max,
    rsrp_dbm,
    anomaly_flag,

    -- ── Derived: latency_ms (deterministic engineering proxy) ──────────────
    -- 3GPP TR 38.913 + Huawei eRAN handbook RTT baselines per RAT.
    -- Linear penalty for integrity loss + multiplicative for CDR.
    --   latency = base_rtt[RAT] + 0.6 × (100 − integrity) + 4.5 × CDR
    --   base_rtt = 18 ms (4G), 55 ms (3G), 95 ms (2G), 30 ms (other)
    GREATEST(0.0,
        CASE rat_type
            WHEN '4G' THEN 18.0
            WHEN '3G' THEN 55.0
            WHEN '2G' THEN 95.0
            ELSE 30.0
        END
        + 0.6 * GREATEST(0.0, 100.0 - COALESCE(integrity, 100.0))
        + 4.5 * COALESCE(call_drop_rate, 0.0)
    ) AS latency_ms_derived,

    -- ── Derived: packet_loss_rate (%) ──────────────────────────────────────
    -- BLER target ≤ 10% per 3GPP. CDR is the strongest signal; integrity
    -- carries residual loss not captured by CDR alone.
    --   loss = clamp[0, 15] (0.5 × CDR + 0.08 × (100 − integrity))
    LEAST(15.0, GREATEST(0.0,
        0.5 * COALESCE(call_drop_rate, 0.0)
        + 0.08 * GREATEST(0.0, 100.0 - COALESCE(integrity, 100.0))
    )) AS packet_loss_pct_derived,

    -- ── Derived: jitter_ms ─────────────────────────────────────────────────
    -- Cellular jitter empirically tracks ~15-20% of latency under load.
    GREATEST(0.0,
        0.18 * (
            CASE rat_type
                WHEN '4G' THEN 18.0
                WHEN '3G' THEN 55.0
                WHEN '2G' THEN 95.0
                ELSE 30.0
            END
            + 0.6 * GREATEST(0.0, 100.0 - COALESCE(integrity, 100.0))
            + 4.5 * COALESCE(call_drop_rate, 0.0)
        )
    ) AS jitter_ms_derived,

    -- ── Real cell_load: avg/max users × 100 (4G only, requires both fields) ─
    -- NULL for 2G/3G and for 4G rows where active_users_max not yet ingested.
    CASE
        WHEN active_users IS NOT NULL
         AND active_users_max IS NOT NULL
         AND active_users_max > 0
        THEN LEAST(100.0, active_users::float / active_users_max::float * 100.0)
        ELSE NULL
    END AS cell_load_pct_real

FROM oss_cell_kpis;

COMMENT ON VIEW vw_oss_cell_derived IS
    'Real Huawei OSS measurements + engineered proxies. Latency, loss, jitter '
    'are DETERMINISTIC formulas keyed on integrity, call_drop_rate, rat_type. '
    'cell_load_pct_real is REAL (4G only) computed from L.Traffic.User.Avg / '
    'L.Traffic.User.Max. Documented in docs/db/migrations/004_oss_derived_view.sql.';

-- Helpful indexes for the timestamp-bucketed queries the PDF + dashboard hit.
CREATE INDEX IF NOT EXISTS idx_oss_cell_timestamp ON oss_cell_kpis (timestamp);
CREATE INDEX IF NOT EXISTS idx_oss_cell_anomaly   ON oss_cell_kpis (anomaly_flag) WHERE anomaly_flag = TRUE;

COMMIT;
