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

export async function GET(req: NextRequest) {
    const cookieStore = cookies();
    const token = cookieStore.get("auth_token")?.value;

    const [sla, history, anomalies, revenue, correlations, runs] = await Promise.all([
        safeFetch("/sla-risk", token),
        safeFetch("/sla-risk/history", token),
        safeFetch("/anomalies", token),
        safeFetch("/revenue-anomalies", token),
        safeFetch("/correlation", token),
        safeFetch("/pipeline-runs", token),
    ]);

    return NextResponse.json({
        sla,
        history: history || [],
        anomalies: anomalies?.anomalies ?? [],
        revenueAnomalies: revenue?.revenue_anomalies ?? [],
        correlations: correlations?.correlations ?? [],
        pipelineRuns: runs ?? [],
    });
}
