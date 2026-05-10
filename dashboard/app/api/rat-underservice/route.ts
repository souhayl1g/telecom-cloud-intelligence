import { NextResponse } from 'next/server';
import { query } from '../../../lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
    try {
        const [overallRow, byGeneration, byArea, topUnderserved] = await Promise.all([
            query<{ total: number; underserved: number; rate: number }>(
                `SELECT rat_total::int       AS total,
                        rat_underserved::int AS underserved,
                        rat_rate             AS rate
                 FROM mv_dashboard_summary`
            ),
            query<{ generation: string; total: number; underserved: number; rate: number }>(
                `SELECT generation, total, underserved, rate
                 FROM mv_rat_by_generation
                 ORDER BY rate DESC`
            ),
            query<{ area: string; total: number; underserved: number; rate: number }>(
                `SELECT area, total, underserved, rate
                 FROM mv_rat_by_area
                 ORDER BY rate DESC
                 LIMIT 30`
            ),
            query<{ imsi_hash: string; rat_gap_score: number; area: string; generation: string; highest_rat: string }>(
                `SELECT imsi_hash, rat_gap_score, area, generation, highest_rat
                 FROM mv_rat_top_underserved
                 ORDER BY rat_gap_score DESC
                 LIMIT 50`
            ),
        ]);

        return NextResponse.json({
            overall: overallRow[0] ?? { total: 0, underserved: 0, rate: 0 },
            byGeneration,
            byArea,
            topUnderserved,
        });
    } catch (err: any) {
        console.error('RAT underservice error:', err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
