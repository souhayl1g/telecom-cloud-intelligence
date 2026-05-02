import { NextResponse } from 'next/server';
import { query } from '../../../lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
    try {
        const overall = await query<{ total: number; underserved: number; rate: number }>(`
            SELECT 
                COUNT(*)::int as total,
                COUNT(*) FILTER (WHERE rat_gap_score > 0.3)::int as underserved,
                ROUND(COUNT(*) FILTER (WHERE rat_gap_score > 0.3) * 100.0 / COUNT(*), 2) as rate
            FROM subscriber_features
            WHERE rat_gap_score IS NOT NULL
        `);

        const byGeneration = await query<{ generation: string; total: number; underserved: number; rate: number }>(`
            SELECT 
                bs.generation,
                COUNT(*)::int as total,
                COUNT(*) FILTER (WHERE sf.rat_gap_score > 0.3)::int as underserved,
                ROUND(COUNT(*) FILTER (WHERE sf.rat_gap_score > 0.3) * 100.0 / COUNT(*), 2) as rate
            FROM subscriber_features sf
            JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
            WHERE sf.rat_gap_score IS NOT NULL AND bs.generation IS NOT NULL
            GROUP BY bs.generation
            ORDER BY rate DESC
        `);

        const byArea = await query<{ area: string; total: number; underserved: number; rate: number }>(`
            SELECT 
                bs.area,
                COUNT(*)::int as total,
                COUNT(*) FILTER (WHERE sf.rat_gap_score > 0.3)::int as underserved,
                ROUND(COUNT(*) FILTER (WHERE sf.rat_gap_score > 0.3) * 100.0 / COUNT(*), 2) as rate
            FROM subscriber_features sf
            JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
            WHERE sf.rat_gap_score IS NOT NULL AND bs.area IS NOT NULL
            GROUP BY bs.area
            ORDER BY rate DESC
        `);

        const topUnderserved = await query<{ imsi_hash: string; rat_gap_score: number; area: string; generation: string; highest_rat: string }>(`
            SELECT 
                sf.imsi_hash,
                sf.rat_gap_score,
                bs.area,
                bs.generation,
                bs.highest_rat
            FROM subscriber_features sf
            JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
            WHERE sf.rat_gap_score IS NOT NULL
            ORDER BY sf.rat_gap_score DESC
            LIMIT 50
        `);

        return NextResponse.json({
            overall: overall[0],
            byGeneration,
            byArea,
            topUnderserved,
        });
    } catch (err: any) {
        console.error('RAT underservice error:', err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
