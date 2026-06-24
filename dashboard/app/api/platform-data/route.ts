import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { query } from "../../../lib/db";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function safeFetch(path: string, token?: string) {
    try {
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${base}${path}`, { cache: "no-store", headers });
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

async function safePost(path: string, body: any, token?: string) {
    try {
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${base}${path}`, {
            method: "POST",
            cache: "no-store",
            headers,
            body: JSON.stringify(body),
        });
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

async function safePatch(path: string, body: any, token?: string) {
    try {
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${base}${path}`, {
            method: "PATCH",
            cache: "no-store",
            headers,
            body: JSON.stringify(body),
        });
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

async function safeQuery<T = any>(sql: string, params?: any[]): Promise<T[]> {
    try {
        return await query<T>(sql, params);
    } catch (err: any) {
        console.error("[platform-data] DB query failed:", err?.message || err);
        return [];
    }
}

export async function GET(_req: NextRequest) {
    const cookieStore = cookies();
    const token = cookieStore.get("auth_token")?.value;

    const [
        correlations,
        runs,
        kpiSummary,
        actions,
        infraStats,
        platformStats,
        granger,
        areas,
        anomalies,           // OSS cell anomalies (from oss_cell_kpis, anomaly_flag = TRUE)
        cemAnomalies,        // CEM-impacting subscriber risk (from subscriber_features, RAT or churn flag)
        vaeSummary,
        cemSummary,
        ratSummary,
        ticketsStats,
        notificationsStats,
        interventionsStats,
        autonomyConfig,      // L4 closed-loop safety envelope (armed/threshold/whitelist/...)
    ] = await Promise.all([
        safeFetch("/correlation", token),
        safeFetch("/pipeline-runs", token),
        safeFetch("/kpi-summary", token),
        safeFetch("/actions", token),
        safeFetch("/infra-stats", token),
        safeFetch("/platform-stats", token),
        safeFetch("/granger-causality", token),
        safeFetch("/areas", token),
        safeQuery(`
            SELECT cell_id, area, rat_type, throughput_mbps,
                   latency_ms_derived       AS latency_ms,
                   packet_loss_pct_derived  AS packet_loss_rate,
                   cell_load_pct_real       AS cell_load_pct,
                   integrity, call_drop_rate, rsrp_dbm, active_users,
                   anomaly_flag,
                   /* Severity: composite of integrity drop + CDR breach + derived loss */
                   LEAST(1.0, GREATEST(0.0,
                       0.5 * (1.0 - COALESCE(integrity, 100.0) / 100.0)
                     + 0.3 * LEAST(1.0, COALESCE(call_drop_rate, 0.0) / 5.0)
                     + 0.2 * LEAST(1.0, COALESCE(packet_loss_pct_derived, 0.0) / 10.0)
                   ))::float8 AS severity,
                   timestamp AS ts
              FROM vw_oss_cell_derived
             WHERE anomaly_flag = TRUE
             ORDER BY timestamp DESC
             LIMIT 200
        `),
        safeQuery(`
            SELECT imsi_hash,
                   NULL::float8 AS cem_score,
                   rat_gap_score,
                   NULL::boolean AS churn_risk_flag,
                   rat_gap_score AS severity,
                   NOW() AS created_at
              FROM mv_rat_top_underserved
             ORDER BY rat_gap_score DESC
             LIMIT 200
        `),
        safeQuery(`
            SELECT oss_total::int          AS total,
                   oss_anomaly_count::int  AS anomaly_count,
                   oss_anomaly_rate        AS anomaly_rate,
                   oss_areas_affected      AS areas_affected
              FROM mv_dashboard_summary
        `),
        safeQuery(`
            SELECT cem_total::int      AS total,
                   cem_avg_score       AS avg_score,
                   cem_poor_count::int AS poor_count,
                   cem_fair_count::int AS fair_count,
                   cem_good_count::int AS good_count
              FROM mv_dashboard_summary
        `),
        safeQuery(`
            SELECT rat_total::int       AS total,
                   rat_underserved::int AS underserved,
                   rat_rate             AS rate
              FROM mv_dashboard_summary
        `),
        safeFetch("/tickets/stats", token),
        safeFetch("/notifications/stats", token),
        safeFetch("/interventions/stats", token),
        safeFetch("/autonomy/config", token),
    ]);

    return NextResponse.json({
        anomalies: anomalies ?? [],
        cemAnomalies: cemAnomalies ?? [],
        correlations: correlations?.correlations ?? [],
        pipelineRuns: runs ?? [],
        kpiSummary: kpiSummary ?? [],
        actions: actions ?? [],
        infraStats: infraStats ?? null,
        platformStats: platformStats ?? null,
        areas: areas?.areas ?? [],
        granger: {
            results: granger?.results ?? [],
            count: (granger?.results ?? []).length,
            significant: (granger?.results ?? []).filter((r: any) => r.significant).length,
        },
        vaeSummary: vaeSummary?.[0] ?? null,
        cemSummary: cemSummary?.[0] ?? null,
        ratSummary: ratSummary?.[0] ?? null,
        ticketsStats: ticketsStats ?? {},
        notificationsStats: notificationsStats ?? {},
        interventionsStats: interventionsStats ?? {},
        autonomyConfig: autonomyConfig ?? null,
    });
}

export async function POST(req: NextRequest) {
    const cookieStore = cookies();
    const token = cookieStore.get("auth_token")?.value;
    const body = await req.json();
    const { _action, ...payload } = body;

    if (_action === "create") {
        const result = await safePost("/actions", payload, token);
        return NextResponse.json(result ?? { error: "Failed to create action" });
    }
    if (_action === "execute") {
        const result = await safePost(`/actions/${payload.action_id}/execute`, {}, token);
        return NextResponse.json(result ?? { error: "Failed to execute action" });
    }
    if (_action === "auto-run") {
        // Fire the L4 closed-loop tick — server enforces the envelope (armed/threshold/whitelist/rate/kill).
        const result = await safePost("/autonomy/auto-run", {}, token);
        return NextResponse.json(result ?? { error: "Failed to run closed loop" });
    }
    if (_action === "set-autonomy") {
        // Arm/disarm + tune the envelope. Validation happens server-side in PATCH /autonomy/config.
        const result = await safePatch("/autonomy/config", payload, token);
        return NextResponse.json(result ?? { error: "Failed to update autonomy config" });
    }

    return NextResponse.json({ error: "Unknown action" }, { status: 400 });
}

export async function PATCH(req: NextRequest) {
    const cookieStore = cookies();
    const token = cookieStore.get("auth_token")?.value;
    const body = await req.json();
    const { action_id, ...payload } = body;

    const result = await safePatch(`/actions/${action_id}`, payload, token);
    return NextResponse.json(result ?? { error: "Failed to update action" });
}
