import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { query } from '../../../lib/db';

export const dynamic = 'force-dynamic';

const base = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

async function safeFetch(path: string, token?: string) {
    try {
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const r = await fetch(`${base}${path}`, { cache: 'no-store', headers });
        if (!r.ok) return null;
        return await r.json();
    } catch { return null; }
}

export async function GET() {
    const token = cookies().get('auth_token')?.value;

    try {
        const [
            summaryRow,
            byArea,
            byCell,
            recentAnomalies,
            reconBins,
            byAreaMonthly,        // NEW: time-series for map animation
            grangerResp,          // NEW: causal pairs for detail panel
        ] = await Promise.all([
            query<{ total: number; anomaly_count: number; anomaly_rate: number; avg_cell_load_anomalous: number }>(
                `SELECT oss_total::int        AS total,
                        oss_anomaly_count::int AS anomaly_count,
                        oss_anomaly_rate       AS anomaly_rate,
                        oss_avg_load_anom      AS avg_cell_load_anomalous
                 FROM mv_dashboard_summary`
            ),
            query<{ area: string; total: number; anomaly_count: number; rate: number }>(
                `SELECT area, total, anomaly_count, rate
                 FROM mv_oss_by_area
                 ORDER BY anomaly_count DESC
                 LIMIT 1500`
            ),
            query<{ cell_id: string; area: string; total: number; anomaly_count: number; rate: number }>(
                `SELECT cell_id, area, total, anomaly_count, rate
                 FROM mv_oss_by_cell
                 ORDER BY anomaly_count DESC
                 LIMIT 30`
            ),
            query<{ cell_id: string; area: string; throughput_mbps: number; latency_ms: number; packet_loss_rate: number; cell_load_pct: number; timestamp: string }>(
                `SELECT cell_id, area, throughput_mbps, latency_ms,
                        packet_loss_rate, cell_load_pct, ts::text AS timestamp
                 FROM mv_oss_recent_anomalies
                 ORDER BY ts DESC
                 LIMIT 50`
            ),
            query<{ bin: number; anomaly_flag: boolean; cnt: number }>(
                `SELECT bin, anomaly_flag, cnt FROM mv_vae_recon_error ORDER BY bin`
            ),
            // Per-month-per-area aggregation for map animation frames.
            // Backed by mv_oss_by_month_area (refreshed per pipeline cycle).
            // Previous implementation aggregated 18M+ rows of oss_cell_kpis
            // on every request — ~12s per call, made the page hang.
            query<{ month_year: string; area: string; total: number; anomaly_count: number; rate: number }>(
                `SELECT month_year, area, total, anomaly_count, rate
                 FROM mv_oss_by_month_area
                 ORDER BY month_year ASC, anomaly_count DESC`
            ),
            // NEW — Granger causality results from prod engine (no auth → 500; that's fine, panel shows empty).
            safeFetch('/granger-causality?limit=500', token),
        ]);

        const threshold = 0.23654;
        const binData = Array.from({ length: 20 }, () => ({ normal: 0, anomaly: 0 }));
        for (const row of reconBins) {
            const idx = row.bin;
            if (idx >= 0 && idx < 20) {
                if (row.anomaly_flag) binData[idx].anomaly = row.cnt;
                else binData[idx].normal = row.cnt;
            }
        }
        const reconstructionError = binData.map((b, i) => {
            const binStart = (i / 20) * 0.6;
            const binEnd = ((i + 1) / 20) * 0.6;
            const binCenter = ((binStart + binEnd) / 2).toFixed(3);
            return { bin: binCenter, normal: b.normal, anomaly: b.anomaly };
        });

        return NextResponse.json({
            summary: summaryRow[0] ?? { total: 0, anomaly_count: 0, anomaly_rate: 0, avg_cell_load_anomalous: 0 },
            byArea,
            byCell,
            recentAnomalies,
            reconstructionError,
            threshold,
            byAreaMonthly,
            granger: grangerResp?.results ?? [],
        });
    } catch (err: any) {
        console.error('VAE anomalies error:', err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
