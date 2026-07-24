-- ═══════════════════════════════════════════════════════════════════════════
-- Dashboard Summary Materialized Views
-- Purpose: pre-aggregate heavy stats so /api/* routes hit indexed 30-row
-- summary tables instead of 19M+row scans. Refresh after each pipeline run.
--
-- BSS/CEM/RAT subscriber aggregates are scoped to the documented CEM corpus
-- (Jan–May 2026, month_year <= '2026-05' = 2,468,026 ≈ 2.47M) so every page's
-- subscriber count matches the data-lake headline. The live tables hold more
-- months (operational twin drift); OSS aggregates keep their full 18.8M scope.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. Single-row global summary ─────────────────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_summary CASCADE;
CREATE MATERIALIZED VIEW mv_dashboard_summary AS
WITH oss AS (
    SELECT
        COUNT(*)::bigint AS oss_total,
        COUNT(*) FILTER (WHERE anomaly_flag = TRUE)::bigint AS oss_anomaly_count,
        COALESCE(ROUND(COUNT(*) FILTER (WHERE anomaly_flag = TRUE) * 100.0
                / NULLIF(COUNT(*),0), 2), 0)::float8 AS oss_anomaly_rate,
        COALESCE(ROUND(AVG(cell_load_pct) FILTER (WHERE anomaly_flag = TRUE)::numeric, 2), 0)::float8 AS oss_avg_load_anom,
        COUNT(DISTINCT area) FILTER (WHERE anomaly_flag = TRUE
            AND area IS NOT NULL
            AND UPPER(TRIM(area)) NOT IN ('NULL','NONE','N/A',''))::int AS oss_areas_affected
    FROM oss_cell_kpis
),
cem AS (
    SELECT
        COUNT(*)::bigint AS cem_total,
        COALESCE(ROUND(AVG(cem_score)::numeric, 4), 0)::float8 AS cem_avg_score,
        COUNT(*) FILTER (WHERE cem_score < 0.3)::bigint AS cem_poor_count,
        COUNT(*) FILTER (WHERE cem_score >= 0.3 AND cem_score < 0.6)::bigint AS cem_fair_count,
        COUNT(*) FILTER (WHERE cem_score >= 0.6)::bigint AS cem_good_count
    FROM subscriber_features
    WHERE cem_score IS NOT NULL
      AND month_year <= '2026-05'
),
rat AS (
    SELECT
        COUNT(*)::bigint AS rat_total,
        COUNT(*) FILTER (WHERE rat_gap_score > 0.3)::bigint AS rat_underserved,
        COALESCE(ROUND(COUNT(*) FILTER (WHERE rat_gap_score > 0.3) * 100.0
                / NULLIF(COUNT(*),0), 2), 0)::float8 AS rat_rate
    FROM subscriber_features
    WHERE rat_gap_score IS NOT NULL
      AND month_year <= '2026-05'
)
SELECT
    1::int AS singleton,
    NOW() AS refreshed_at,
    oss.*, cem.*, rat.*
FROM oss, cem, rat;

CREATE UNIQUE INDEX ON mv_dashboard_summary (singleton);

-- ── 2. OSS anomaly aggs by area ──────────────────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_oss_by_area CASCADE;
CREATE MATERIALIZED VIEW mv_oss_by_area AS
SELECT
    area,
    COUNT(*)::int AS total,
    COUNT(*) FILTER (WHERE anomaly_flag = TRUE)::int AS anomaly_count,
    COALESCE(ROUND(COUNT(*) FILTER (WHERE anomaly_flag = TRUE) * 100.0
            / NULLIF(COUNT(*),0), 2), 0)::float8 AS rate
FROM oss_cell_kpis
WHERE area IS NOT NULL AND UPPER(TRIM(area)) NOT IN ('NULL','NONE','N/A','')
GROUP BY area
HAVING COUNT(*) >= 10;

CREATE UNIQUE INDEX ON mv_oss_by_area (area);
CREATE INDEX ON mv_oss_by_area (anomaly_count DESC);

-- ── 3. OSS aggs by cell ──────────────────────────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_oss_by_cell CASCADE;
CREATE MATERIALIZED VIEW mv_oss_by_cell AS
SELECT
    cell_id,
    area,
    COUNT(*)::int AS total,
    COUNT(*) FILTER (WHERE anomaly_flag = TRUE)::int AS anomaly_count,
    COALESCE(ROUND(COUNT(*) FILTER (WHERE anomaly_flag = TRUE) * 100.0
            / NULLIF(COUNT(*),0), 2), 0)::float8 AS rate
FROM oss_cell_kpis
GROUP BY cell_id, area
ORDER BY anomaly_count DESC
LIMIT 100;

CREATE UNIQUE INDEX ON mv_oss_by_cell (cell_id, area);
CREATE INDEX ON mv_oss_by_cell (anomaly_count DESC);

-- ── 3b. OSS aggs by month + area (powers VAE map animation) ─────────────
-- Aggregating 18M+ rows of oss_cell_kpis on every dashboard request was
-- ~12s wall-clock and made /api/vae-anomalies hang. Materialized → ms.
DROP MATERIALIZED VIEW IF EXISTS mv_oss_by_month_area CASCADE;
CREATE MATERIALIZED VIEW mv_oss_by_month_area AS
SELECT
    month_year,
    area,
    COUNT(*)::int AS total,
    COUNT(*) FILTER (WHERE anomaly_flag = TRUE)::int AS anomaly_count,
    COALESCE(ROUND(COUNT(*) FILTER (WHERE anomaly_flag = TRUE) * 100.0
            / NULLIF(COUNT(*),0), 2), 0)::float8 AS rate
FROM oss_cell_kpis
WHERE area IS NOT NULL
  AND UPPER(TRIM(area)) NOT IN ('NULL','NONE','N/A','')
GROUP BY month_year, area
HAVING COUNT(*) >= 10;

CREATE UNIQUE INDEX ON mv_oss_by_month_area (month_year, area);

-- ── 4. Recent OSS anomalies (already-joined rows) ─────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_oss_recent_anomalies CASCADE;
CREATE MATERIALIZED VIEW mv_oss_recent_anomalies AS
SELECT
    id,
    cell_id,
    area,
    throughput_mbps,
    latency_ms,
    packet_loss_rate,
    cell_load_pct,
    created_at AS ts
FROM oss_cell_kpis
WHERE anomaly_flag = TRUE
  AND area IS NOT NULL
  AND UPPER(TRIM(area)) NOT IN ('NULL','NONE','N/A','')
ORDER BY created_at DESC
LIMIT 200;

CREATE UNIQUE INDEX ON mv_oss_recent_anomalies (id);

-- ── 5. CEM distribution histogram ─────────────────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_cem_distribution CASCADE;
CREATE MATERIALIZED VIEW mv_cem_distribution AS
SELECT
    width_bucket(cem_score, 0, 1, 20) AS bucket,
    COUNT(*)::int AS count,
    MIN(cem_score)::float8 AS min_score,
    MAX(cem_score)::float8 AS max_score
FROM subscriber_features
WHERE cem_score IS NOT NULL
  AND month_year <= '2026-05'
GROUP BY bucket;

CREATE UNIQUE INDEX ON mv_cem_distribution (bucket);

-- ── 6. CEM by area (joined with bss_subscribers) ──────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_cem_by_area CASCADE;
CREATE MATERIALIZED VIEW mv_cem_by_area AS
SELECT
    bs.area,
    ROUND(AVG(sf.cem_score)::numeric, 4)::float8 AS avg_cem_score,
    COUNT(*)::int AS subscriber_count
FROM subscriber_features sf
JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
WHERE sf.cem_score IS NOT NULL
  AND sf.month_year <= '2026-05'
  AND bs.area IS NOT NULL
  AND UPPER(TRIM(bs.area)) NOT IN ('NULL','NONE','N/A','')
GROUP BY bs.area
HAVING COUNT(*) >= 10;

CREATE UNIQUE INDEX ON mv_cem_by_area (area);
CREATE INDEX ON mv_cem_by_area (avg_cem_score DESC);

-- ── 7. Top highest CEM subscribers (joined) ──────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_cem_top_highest CASCADE;
CREATE MATERIALIZED VIEW mv_cem_top_highest AS
SELECT
    sf.imsi_hash,
    sf.cem_score::float8 AS cem_score,
    bs.area,
    bs.generation
FROM subscriber_features sf
JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
WHERE sf.cem_score IS NOT NULL
  AND sf.month_year <= '2026-05'
  AND bs.area IS NOT NULL
  AND UPPER(TRIM(bs.area)) NOT IN ('NULL','NONE','N/A','')
ORDER BY sf.cem_score DESC
LIMIT 50;

CREATE UNIQUE INDEX ON mv_cem_top_highest (imsi_hash);

-- ── 8. Top lowest CEM subscribers (joined) ───────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_cem_top_lowest CASCADE;
CREATE MATERIALIZED VIEW mv_cem_top_lowest AS
SELECT
    sf.imsi_hash,
    sf.cem_score::float8 AS cem_score,
    bs.area,
    bs.generation
FROM subscriber_features sf
JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
WHERE sf.cem_score IS NOT NULL
  AND sf.month_year <= '2026-05'
  AND bs.area IS NOT NULL
  AND UPPER(TRIM(bs.area)) NOT IN ('NULL','NONE','N/A','')
ORDER BY sf.cem_score ASC
LIMIT 50;

CREATE UNIQUE INDEX ON mv_cem_top_lowest (imsi_hash);

-- ── 9. RAT underservice by generation (joined) ───────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_rat_by_generation CASCADE;
CREATE MATERIALIZED VIEW mv_rat_by_generation AS
SELECT
    bs.generation,
    COUNT(*)::int AS total,
    COUNT(*) FILTER (WHERE sf.rat_gap_score > 0.3)::int AS underserved,
    COALESCE(ROUND(COUNT(*) FILTER (WHERE sf.rat_gap_score > 0.3) * 100.0
            / NULLIF(COUNT(*),0), 2), 0)::float8 AS rate
FROM subscriber_features sf
JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
WHERE sf.rat_gap_score IS NOT NULL
  AND sf.month_year <= '2026-05'
  AND bs.generation IS NOT NULL
  AND UPPER(TRIM(bs.generation)) NOT IN ('NULL','NONE','N/A','')
GROUP BY bs.generation;

CREATE UNIQUE INDEX ON mv_rat_by_generation (generation);

-- ── 10. RAT underservice by area (joined) ────────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_rat_by_area CASCADE;
CREATE MATERIALIZED VIEW mv_rat_by_area AS
SELECT
    bs.area,
    COUNT(*)::int AS total,
    COUNT(*) FILTER (WHERE sf.rat_gap_score > 0.3)::int AS underserved,
    COALESCE(ROUND(COUNT(*) FILTER (WHERE sf.rat_gap_score > 0.3) * 100.0
            / NULLIF(COUNT(*),0), 2), 0)::float8 AS rate
FROM subscriber_features sf
JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
WHERE sf.rat_gap_score IS NOT NULL
  AND sf.month_year <= '2026-05'
  AND bs.area IS NOT NULL
  AND UPPER(TRIM(bs.area)) NOT IN ('NULL','NONE','N/A','')
GROUP BY bs.area
HAVING COUNT(*) >= 10;

CREATE UNIQUE INDEX ON mv_rat_by_area (area);
CREATE INDEX ON mv_rat_by_area (rate DESC);

-- ── 11. Top underserved RAT subscribers (joined) ─────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_rat_top_underserved CASCADE;
CREATE MATERIALIZED VIEW mv_rat_top_underserved AS
SELECT
    sf.imsi_hash,
    sf.rat_gap_score::float8 AS rat_gap_score,
    bs.area,
    bs.generation,
    bs.highest_rat
FROM subscriber_features sf
JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
WHERE sf.rat_gap_score IS NOT NULL
  AND sf.month_year <= '2026-05'
  AND bs.area IS NOT NULL
  AND UPPER(TRIM(bs.area)) NOT IN ('NULL','NONE','N/A','')
ORDER BY sf.rat_gap_score DESC
LIMIT 100;

CREATE UNIQUE INDEX ON mv_rat_top_underserved (imsi_hash);

-- ── 12. VAE reconstruction error histogram ───────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS mv_vae_recon_error CASCADE;
CREATE MATERIALIZED VIEW mv_vae_recon_error AS
WITH stats AS (
    SELECT
        AVG(throughput_mbps) FILTER (WHERE anomaly_flag = false) AS m1,
        STDDEV(throughput_mbps) FILTER (WHERE anomaly_flag = false) AS s1,
        AVG(latency_ms) FILTER (WHERE anomaly_flag = false) AS m2,
        STDDEV(latency_ms) FILTER (WHERE anomaly_flag = false) AS s2,
        AVG(packet_loss_rate) FILTER (WHERE anomaly_flag = false) AS m3,
        STDDEV(packet_loss_rate) FILTER (WHERE anomaly_flag = false) AS s3,
        AVG(jitter_ms) FILTER (WHERE anomaly_flag = false) AS m4,
        STDDEV(jitter_ms) FILTER (WHERE anomaly_flag = false) AS s4,
        AVG(cell_load_pct) FILTER (WHERE anomaly_flag = false) AS m5,
        STDDEV(cell_load_pct) FILTER (WHERE anomaly_flag = false) AS s5,
        AVG(rsrp_dbm) FILTER (WHERE anomaly_flag = false) AS m6,
        STDDEV(rsrp_dbm) FILTER (WHERE anomaly_flag = false) AS s6,
        AVG(active_users) FILTER (WHERE anomaly_flag = false) AS m7,
        STDDEV(active_users) FILTER (WHERE anomaly_flag = false) AS s7
    FROM (SELECT * FROM oss_cell_kpis ORDER BY id LIMIT 200000) sample
),
errors AS (
    SELECT
        anomaly_flag,
        (
            CASE WHEN s1 > 0 THEN ((throughput_mbps - m1)/s1)^2 ELSE 0 END +
            CASE WHEN s2 > 0 THEN ((latency_ms - m2)/s2)^2 ELSE 0 END +
            CASE WHEN s3 > 0 THEN ((packet_loss_rate - m3)/s3)^2 ELSE 0 END +
            CASE WHEN s4 > 0 THEN ((jitter_ms - m4)/s4)^2 ELSE 0 END +
            CASE WHEN s5 > 0 THEN ((cell_load_pct - m5)/s5)^2 ELSE 0 END +
            CASE WHEN s6 > 0 THEN ((rsrp_dbm - m6)/s6)^2 ELSE 0 END +
            CASE WHEN s7 > 0 THEN ((active_users - m7)/s7)^2 ELSE 0 END
        ) / 7.0 AS recon_error
    FROM (SELECT * FROM oss_cell_kpis ORDER BY id LIMIT 200000) sample, stats
)
SELECT
    LEAST(GREATEST(FLOOR(recon_error / 0.03), 0), 19)::int AS bin,
    anomaly_flag,
    COUNT(*)::int AS cnt
FROM errors
WHERE recon_error IS NOT NULL
GROUP BY bin, anomaly_flag;

CREATE UNIQUE INDEX ON mv_vae_recon_error (bin, anomaly_flag);

-- ── 13. Refresh function ─────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION refresh_dashboard_views() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_oss_by_area;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_oss_by_month_area;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_oss_by_cell;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_oss_recent_anomalies;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_cem_distribution;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_cem_by_area;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_cem_top_highest;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_cem_top_lowest;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_rat_by_generation;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_rat_by_area;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_rat_top_underserved;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_vae_recon_error;
END;
$$ LANGUAGE plpgsql;
