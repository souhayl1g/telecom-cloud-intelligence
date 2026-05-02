import { NextResponse } from "next/server";

type ServiceCheck = {
    id: string;
    name: string;
    category: "api" | "ml" | "auth" | "data" | "worker" | "ui" | "obs";
    url: string;
    publicUrl?: string;
    port: number;
    status: "up" | "down" | "unknown";
    latencyMs: number | null;
    statusCode: number | null;
    error?: string;
};

const SERVICES: Omit<ServiceCheck, "status" | "latencyMs" | "statusCode" | "error">[] = [
    { id: "api-gateway",   name: "API Gateway",     category: "api",    url: "http://api-gateway:8000/health",   publicUrl: "http://localhost:8000/docs", port: 8000 },
    { id: "ai-service",    name: "AI Service",      category: "ml",     url: "http://ai-service:8001/health",    publicUrl: "http://localhost:8001/docs", port: 8001 },
    { id: "auth-service",  name: "Auth Service",    category: "auth",   url: "http://auth-service:8002/health",  publicUrl: "http://localhost:8002/docs", port: 8002 },
    { id: "agent-service", name: "Agent Service",   category: "ml",     url: "http://agent-service:8003/health", publicUrl: "http://localhost:8003/docs", port: 8003 },
    { id: "minio",         name: "MinIO Storage",   category: "data",   url: "http://minio:9000/minio/health/live", publicUrl: "http://localhost:9001", port: 9000 },
    { id: "postgres",      name: "PostgreSQL",      category: "data",   url: "http://api-gateway:8000/health",   port: 5432 },
    { id: "pipeline",      name: "Pipeline Worker", category: "worker", url: "http://api-gateway:8000/pipeline-runs?limit=1", port: 0 },
    { id: "signoz",        name: "SigNoz",          category: "obs",    url: "http://signoz-frontend:3301",       publicUrl: "http://localhost:3301", port: 3301 },
    { id: "otel",          name: "OTel Collector",  category: "obs",    url: "http://otel-collector:13133",       publicUrl: "http://localhost:4318", port: 4317 },
    { id: "clickhouse",    name: "ClickHouse",      category: "obs",    url: "http://clickhouse:8123/ping",       port: 9000 },
];

async function ping(url: string, timeoutMs = 3000): Promise<{ ok: boolean; latencyMs: number; status: number | null; error?: string }> {
    const started = Date.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, { cache: "no-store", signal: controller.signal });
        return { ok: res.ok || res.status === 401, latencyMs: Date.now() - started, status: res.status };
    } catch (e: any) {
        return { ok: false, latencyMs: Date.now() - started, status: null, error: e?.message || "unreachable" };
    } finally {
        clearTimeout(timer);
    }
}

export async function GET() {
    const results: ServiceCheck[] = await Promise.all(
        SERVICES.map(async (svc) => {
            const r = await ping(svc.url);
            return {
                ...svc,
                status: r.ok ? "up" : "down",
                latencyMs: r.latencyMs,
                statusCode: r.status,
                error: r.error,
            };
        })
    );

    const up = results.filter((r) => r.status === "up").length;
    const down = results.length - up;
    const overall: "healthy" | "degraded" | "down" =
        down === 0 ? "healthy" : up === 0 ? "down" : "degraded";

    return NextResponse.json({
        overall,
        up,
        down,
        total: results.length,
        services: results,
        checkedAt: new Date().toISOString(),
    });
}
