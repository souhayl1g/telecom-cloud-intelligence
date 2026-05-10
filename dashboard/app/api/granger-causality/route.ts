import { NextResponse } from "next/server";
import { query } from "../../../lib/db";

export async function GET() {
    // Skip DB connection during Next.js static generation / build
    if (process.env.NEXT_PHASE === 'phase-production-build') {
        return NextResponse.json({ results: [], summaries: [] });
    }
    try {
        const results = await query<any>(
            `SELECT
                area,
                oss_variable,
                cem_variable,
                direction,
                max_lag::int as max_lag,
                best_lag::int as best_lag,
                best_pvalue::float8 as best_pvalue,
                best_fstat::float8 as best_fstat,
                significant,
                created_at
            FROM granger_causality_results
            ORDER BY significant DESC, best_pvalue ASC
            LIMIT 500`
        );

        const summaries = await query<any>(
            `SELECT
                oss_variable,
                cem_variable,
                COUNT(*)::int as total_tests,
                SUM(CASE WHEN significant THEN 1 ELSE 0 END)::int as significant_count,
                (ROUND(AVG(best_lag)::numeric, 1))::float8 as mean_lag,
                (ROUND(AVG(best_pvalue)::numeric, 4))::float8 as mean_pvalue,
                (ROUND(100.0 * SUM(CASE WHEN significant THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1))::float8 as significance_pct
            FROM granger_causality_results
            GROUP BY oss_variable, cem_variable
            ORDER BY significance_pct DESC, mean_pvalue ASC`
        );

        return NextResponse.json({ results: results ?? [], summaries: summaries ?? [] });
    } catch (e: any) {
        console.error("[granger-causality] error:", e?.message || e);
        // Return empty data gracefully so the dashboard doesn't crash during build
        return NextResponse.json({ results: [], summaries: [], error: e?.message || "Database error" });
    }
}
