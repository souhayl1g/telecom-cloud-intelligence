import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

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

export async function GET(req: NextRequest) {
    const cookieStore = cookies();
    const token = cookieStore.get("auth_token")?.value;

    const [sla, history, anomalies, revenue, correlations, runs, anomalyStats, kpiSummary, actions, infraStats, areas] = await Promise.all([
        safeFetch("/sla-risk", token),
        safeFetch("/sla-risk/history", token),
        safeFetch("/anomalies", token),
        safeFetch("/revenue-anomalies", token),
        safeFetch("/correlation", token),
        safeFetch("/pipeline-runs", token),
        safeFetch("/anomaly-stats", token),
        safeFetch("/kpi-summary", token),
        safeFetch("/actions", token),
        safeFetch("/infra-stats", token),
        safeFetch("/areas", token),
    ]);

    return NextResponse.json({
        sla,
        history: history || [],
        anomalies: anomalies?.anomalies ?? [],
        revenueAnomalies: revenue?.revenue_anomalies ?? [],
        correlations: correlations?.correlations ?? [],
        pipelineRuns: runs ?? [],
        anomalyStats: anomalyStats ?? [],
        kpiSummary: kpiSummary ?? [],
        actions: actions ?? [],
        infraStats: infraStats ?? null,
        areas: areas?.areas ?? [],
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
