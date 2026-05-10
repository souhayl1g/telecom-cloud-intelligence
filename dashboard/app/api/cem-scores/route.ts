import { NextResponse } from 'next/server';
import { query } from '../../../lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
    try {
        const [distribution, areaAverages, topHighest, topLowest, summaryRow] = await Promise.all([
            query<{ bucket: number; count: number; min_score: number; max_score: number }>(
                `SELECT bucket, count, min_score, max_score
                 FROM mv_cem_distribution
                 ORDER BY bucket`
            ),
            query<{ area: string; avg_cem_score: number; subscriber_count: number }>(
                `SELECT area, avg_cem_score, subscriber_count
                 FROM mv_cem_by_area
                 ORDER BY avg_cem_score DESC
                 LIMIT 30`
            ),
            query<{ imsi_hash: string; cem_score: number; area: string; generation: string }>(
                `SELECT imsi_hash, cem_score, area, generation
                 FROM mv_cem_top_highest
                 ORDER BY cem_score DESC
                 LIMIT 10`
            ),
            query<{ imsi_hash: string; cem_score: number; area: string; generation: string }>(
                `SELECT imsi_hash, cem_score, area, generation
                 FROM mv_cem_top_lowest
                 ORDER BY cem_score ASC
                 LIMIT 10`
            ),
            query<{ total: number; avg_score: number; poor_count: number; fair_count: number; good_count: number }>(
                `SELECT cem_total::int  AS total,
                        cem_avg_score   AS avg_score,
                        cem_poor_count::int AS poor_count,
                        cem_fair_count::int AS fair_count,
                        cem_good_count::int AS good_count
                 FROM mv_dashboard_summary`
            ),
        ]);

        return NextResponse.json({
            distribution,
            areaAverages,
            topHighest,
            topLowest,
            summary: summaryRow[0] ?? { total: 0, avg_score: 0, poor_count: 0, fair_count: 0, good_count: 0 },
        });
    } catch (err: any) {
        console.error('CEM scores error:', err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
