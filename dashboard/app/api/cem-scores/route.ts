import { NextResponse } from 'next/server';
import { query } from '../../../lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
    try {
        const distribution = await query<{ bucket: number; count: number; min_score: number; max_score: number }>(`
            SELECT 
                width_bucket(cem_score, 0, 1, 20) as bucket,
                COUNT(*) as count,
                MIN(cem_score) as min_score,
                MAX(cem_score) as max_score
            FROM subscriber_features
            WHERE cem_score IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        `);

        const areaAverages = await query<{ area: string; avg_cem_score: number; subscriber_count: number }>(`
            SELECT 
                bs.area,
                ROUND(AVG(sf.cem_score)::numeric, 4) as avg_cem_score,
                COUNT(*)::int as subscriber_count
            FROM subscriber_features sf
            JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
            WHERE sf.cem_score IS NOT NULL AND bs.area IS NOT NULL
            GROUP BY bs.area
            ORDER BY avg_cem_score DESC
        `);

        const topHighest = await query<{ imsi_hash: string; cem_score: number; area: string; generation: string }>(`
            SELECT 
                sf.imsi_hash,
                sf.cem_score,
                bs.area,
                bs.generation
            FROM subscriber_features sf
            JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
            WHERE sf.cem_score IS NOT NULL
            ORDER BY sf.cem_score DESC
            LIMIT 10
        `);

        const topLowest = await query<{ imsi_hash: string; cem_score: number; area: string; generation: string }>(`
            SELECT 
                sf.imsi_hash,
                sf.cem_score,
                bs.area,
                bs.generation
            FROM subscriber_features sf
            JOIN bss_subscribers bs ON sf.imsi_hash = bs.imsi_hash AND sf.month_year = bs.month_year
            WHERE sf.cem_score IS NOT NULL
            ORDER BY sf.cem_score ASC
            LIMIT 10
        `);

        const summary = await query<{ total: number; avg_score: number; poor_count: number; fair_count: number; good_count: number }>(`
            SELECT 
                COUNT(*)::int as total,
                ROUND(AVG(cem_score)::numeric, 4) as avg_score,
                COUNT(*) FILTER (WHERE cem_score < 0.3)::int as poor_count,
                COUNT(*) FILTER (WHERE cem_score >= 0.3 AND cem_score < 0.6)::int as fair_count,
                COUNT(*) FILTER (WHERE cem_score >= 0.6)::int as good_count
            FROM subscriber_features
            WHERE cem_score IS NOT NULL
        `);

        return NextResponse.json({
            distribution,
            areaAverages,
            topHighest,
            topLowest,
            summary: summary[0],
        });
    } catch (err: any) {
        console.error('CEM scores error:', err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
