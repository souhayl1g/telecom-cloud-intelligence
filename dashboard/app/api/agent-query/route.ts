import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { query } from "../../../lib/db";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function liveBrief(userQuery: string): Promise<string> {
    /* Fallback brief built from DB when orchestrator is unreachable.
     * Keeps the L4 chat usable instead of throwing a generic connection error. */
    try {
        const [cemRow] = await query<{ avg: number; total: number; poor: number }>(
            `SELECT COALESCE(AVG(cem_score),0)::float8 AS avg,
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE cem_score < 0.3)::int AS poor
               FROM subscriber_features WHERE cem_score IS NOT NULL`
        );
        const [vaeRow] = await query<{ total: number; anom: number }>(
            `SELECT COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE anomaly_flag = TRUE)::int AS anom
               FROM oss_cell_kpis`
        );
        const [ratRow] = await query<{ under: number; rate: number }>(
            `SELECT COUNT(*) FILTER (WHERE rat_gap_score > 0.3)::int AS under,
                    (COUNT(*) FILTER (WHERE rat_gap_score > 0.3) * 100.0
                     / NULLIF(COUNT(*),0))::float8 AS rate
               FROM subscriber_features WHERE rat_gap_score IS NOT NULL`
        );
        const [grRow] = await query<{ sig: number; total: number }>(
            `SELECT COUNT(*) FILTER (WHERE significant)::int AS sig,
                    COUNT(*)::int AS total
               FROM granger_causality_results`
        );

        const cem = cemRow?.avg?.toFixed(3) ?? "—";
        const vaeRate = vaeRow?.total ? ((vaeRow.anom / vaeRow.total) * 100).toFixed(2) : "0.00";
        const ratRate = ratRow?.rate?.toFixed(2) ?? "0.00";

        return [
            `[NeXo Live Brief — orchestrator offline, served from local DB]`,
            ``,
            `Your query: "${userQuery}"`,
            ``,
            `Snapshot of platform state right now:`,
            `• CEM avg: ${cem}  (LightGBM v3.0 over ${cemRow?.total?.toLocaleString() ?? 0} subscribers — ${cemRow?.poor?.toLocaleString() ?? 0} poor experience).`,
            `• VAE anomalies: ${vaeRow?.anom?.toLocaleString() ?? 0} / ${vaeRow?.total?.toLocaleString() ?? 0} cells (${vaeRate}% rate).`,
            `• RAT underservice: ${ratRow?.under?.toLocaleString() ?? 0} subscribers (${ratRate}%).`,
            `• Granger: ${grRow?.sig ?? 0} significant causal pairs out of ${grRow?.total ?? 0}.`,
            ``,
            `Note: agent-service is offline so I can't run a tool-calling reasoning trace. Re-run \`docker compose up -d agent-service\` to restore full chat.`,
        ].join("\n");
    } catch {
        return `Agent offline. DB also unreachable. Verify Docker services: docker compose ps`;
    }
}

export async function POST(req: NextRequest) {
    const cookieStore = cookies();
    const token = cookieStore.get("auth_token")?.value;

    if (!token) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    let body: any = {};
    try {
        body = await req.json();
    } catch {
        body = {};
    }

    try {
        const ctrl = new AbortController();
        const timeout = setTimeout(() => ctrl.abort(), 25000);
        const res = await fetch(`${base}/agent/query`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(body),
            cache: "no-store",
            signal: ctrl.signal,
        });
        clearTimeout(timeout);

        if (!res.ok) {
            const fallback = await liveBrief(body?.query ?? "");
            return NextResponse.json({
                response: fallback,
                degraded: true,
                upstream_status: res.status,
                classification: { agent: "fallback", action: "live_brief" },
                agent_result: { agent_name: "Live Brief" },
            });
        }
        return NextResponse.json(await res.json());
    } catch (err: any) {
        const fallback = await liveBrief(body?.query ?? "");
        return NextResponse.json({
            response: fallback,
            degraded: true,
            error: err?.message || "Agent connection failed",
            classification: { agent: "fallback", action: "live_brief" },
            agent_result: { agent_name: "Live Brief" },
        });
    }
}
