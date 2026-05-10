import { cookies } from 'next/headers';
import { query } from './db';

const base = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

async function safe<T>(path: string): Promise<T | null> {
    try {
        const cookieStore = cookies();
        const token = cookieStore.get('auth_token')?.value;

        const headers: Record<string, string> = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const res = await fetch(`${base}${path}`, {
            cache: 'no-store',
            headers,
        });
        if (!res.ok) return null;
        return (await res.json()) as T;
    } catch (err: any) {
        console.error(`[API] ${path} failed:`, err?.message || err);
        return null;
    }
}

async function safeQuery<T = any>(sql: string, params?: any[]): Promise<T[]> {
    try {
        return await query<T>(sql, params);
    } catch (err: any) {
        console.error('[DB] query failed:', err?.message || err);
        return [];
    }
}

export const api = {
    /* ── Gateway-backed (HTTP) ─────────────────────────────────────── */
    correlation: async () =>
        (await safe<{ correlations: Array<any> }>(`/correlation`))?.correlations ?? [],
    pipelineRuns: () => safe<Array<any>>(`/pipeline-runs`),
    kpiSummary: () => safe<Array<any>>(`/kpi-summary`),
    infraStats: () => safe<any>(`/infra-stats`),
    grangerCausality: async () => {
        // Page expects {results, summaries}. Gateway exposes them on two endpoints.
        // Compute summaries from DB directly so we get a single round-trip and avoid
        // double auth hops when gateway is slow.
        const results = await safeQuery<any>(
            `SELECT area, oss_variable, cem_variable, direction,
                    max_lag::int AS max_lag, best_lag::int AS best_lag,
                    best_pvalue::float8 AS best_pvalue, best_fstat::float8 AS best_fstat,
                    significant, created_at
               FROM granger_causality_results
              ORDER BY significant DESC, best_pvalue ASC
              LIMIT 500`
        );
        const summaries = await safeQuery<any>(
            `SELECT oss_variable,
                    cem_variable,
                    COUNT(*)::int AS total_tests,
                    SUM(CASE WHEN significant THEN 1 ELSE 0 END)::int AS significant_count,
                    (ROUND(AVG(best_lag)::numeric, 1))::float8 AS mean_lag,
                    (ROUND(AVG(best_pvalue)::numeric, 4))::float8 AS mean_pvalue,
                    (ROUND(100.0 * SUM(CASE WHEN significant THEN 1 ELSE 0 END)
                          / NULLIF(COUNT(*),0), 1))::float8 AS significance_pct
               FROM granger_causality_results
              GROUP BY oss_variable, cem_variable
              ORDER BY significance_pct DESC NULLS LAST, mean_pvalue ASC NULLS LAST`
        );
        return { results, summaries };
    },
    grangerSummary: async () =>
        await safe<{ summaries: Array<any> }>(`/granger-causality/summary`),
    platformStats: () => safe<any>(`/platform-stats`),
    areas: async () => (await safe<{ areas: Array<any> }>(`/areas`))?.areas ?? [],

    /* ── DB-backed (direct Postgres) ───────────────────────────────── */
    /* OSS cell anomalies — sourced from materialized view (already-joined recent rows) */
    anomalies: async () =>
        await safeQuery<any>(
            `SELECT cell_id, area, throughput_mbps, latency_ms, packet_loss_rate,
                    cell_load_pct, TRUE AS anomaly_flag,
                    LEAST(1.0, GREATEST(0.0, COALESCE(cell_load_pct,0)/100.0))::float AS severity,
                    ts
               FROM mv_oss_recent_anomalies
              ORDER BY ts DESC
              LIMIT 200`
        ),

    /* CEM-impacting subscribers flagged by RAT gap — uses pre-joined materialized view */
    cemAnomalies: async () =>
        await safeQuery<any>(
            `SELECT imsi_hash, NULL::float AS cem_score, rat_gap_score,
                    NULL::boolean AS churn_risk_flag,
                    rat_gap_score AS severity,
                    NOW() AS created_at
               FROM mv_rat_top_underserved
              ORDER BY rat_gap_score DESC
              LIMIT 200`
        ),

    /* Pipeline run anomaly counts — uses summary view counts, no per-row scan */
    anomalyStats: async () =>
        await safeQuery<any>(
            `WITH summary AS (SELECT * FROM mv_dashboard_summary)
             SELECT pr.run_id,
                    pr.status,
                    pr.started_at,
                    pr.finished_at,
                    /* Summary-distributed proxy: rough share of anomalies per run */
                    GREATEST(0, ROUND((SELECT oss_anomaly_count FROM summary)::numeric
                                       / GREATEST((SELECT COUNT(*) FROM pipeline_runs), 1)))::int AS oss_anomaly_count,
                    GREATEST(0, ROUND((SELECT rat_underserved FROM summary)::numeric
                                       / GREATEST((SELECT COUNT(*) FROM pipeline_runs), 1)))::int AS cem_anomaly_count
               FROM pipeline_runs pr
              ORDER BY pr.id DESC
              LIMIT 20`
        ),

    /* VAE summary — reads single-row materialized view (8ms vs 5s) */
    vaeAnomalies: async () => {
        const rows = await safeQuery<{ total: number; anomaly_count: number; anomaly_rate: number }>(
            `SELECT oss_total::int        AS total,
                    oss_anomaly_count::int AS anomaly_count,
                    oss_anomaly_rate       AS anomaly_rate
               FROM mv_dashboard_summary`
        );
        return rows[0] ?? { total: 0, anomaly_count: 0, anomaly_rate: 0 };
    },

    /* CEM summary — reads single-row materialized view */
    cemScores: async () => {
        const rows = await safeQuery<{ total: number; avg_score: number; poor_count: number; fair_count: number; good_count: number }>(
            `SELECT cem_total::int      AS total,
                    cem_avg_score       AS avg_score,
                    cem_poor_count::int AS poor_count,
                    cem_fair_count::int AS fair_count,
                    cem_good_count::int AS good_count
               FROM mv_dashboard_summary`
        );
        return rows[0] ?? { total: 0, avg_score: 0, poor_count: 0, fair_count: 0, good_count: 0 };
    },

    /* RAT underservice summary — reads single-row materialized view */
    ratUnderservice: async () => {
        const rows = await safeQuery<{ total: number; underserved: number; rate: number }>(
            `SELECT rat_total::int       AS total,
                    rat_underserved::int AS underserved,
                    rat_rate             AS rate
               FROM mv_dashboard_summary`
        );
        return rows[0] ?? { total: 0, underserved: 0, rate: 0 };
    },
};
