"use client";

import { useEffect, useMemo, useState } from "react";

type ServiceCheck = {
    id: string;
    name: string;
    category: "api" | "ml" | "auth" | "data" | "worker" | "ui" | "obs";
    publicUrl?: string;
    port: number;
    status: "up" | "down" | "unknown";
    latencyMs: number | null;
    statusCode: number | null;
    error?: string;
};

type HealthPayload = {
    overall: "healthy" | "degraded" | "down";
    up: number;
    down: number;
    total: number;
    services: ServiceCheck[];
    checkedAt: string;
};

const CATEGORY_META: Record<ServiceCheck["category"], { label: string; color: string; icon: string }> = {
    api: { label: "API", color: "var(--color-info)", icon: "⚡" },
    ml: { label: "ML", color: "var(--color-purple)", icon: "🧠" },
    auth: { label: "Auth", color: "var(--brand-accent)", icon: "🔐" },
    data: { label: "Data", color: "var(--color-warning)", icon: "💾" },
    worker: { label: "Pipeline", color: "var(--color-success)", icon: "⚙" },
    ui: { label: "Frontend", color: "var(--brand-primary)", icon: "◆" },
    obs: { label: "Observ.", color: "var(--color-success)", icon: "📡" },
};

export default function OpsMetricsPage() {
    const [data, setData] = useState<HealthPayload | null>(null);
    const [loading, setLoading] = useState(true);
    const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

    const load = async () => {
        try {
            const res = await fetch("/api/health-check", { cache: "no-store" });
            const json = await res.json();
            setData(json);
            setLastRefresh(new Date());
        } catch (_) {
            // keep previous data on transient error
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
        const t = setInterval(load, 15000);
        return () => clearInterval(t);
    }, []);

    const healthPct = useMemo(() => {
        if (!data) return 0;
        return Math.round((data.up / data.total) * 100);
    }, [data]);

    const overallLabel = data?.overall ?? (loading ? "checking" : "unknown");
    const overallColor =
        data?.overall === "healthy" ? "var(--color-success)" :
            data?.overall === "degraded" ? "var(--color-warning)" :
                data?.overall === "down" ? "var(--color-danger)" : "var(--text-muted)";

    return (
        <div className="grid" style={{ gap: 24 }}>
            {/* Hero header */}
            <div className="health-hero">
                <div className="health-hero-left">
                    <div className="health-hero-kicker">Platform Observability</div>
                    <h1 className="health-hero-title">System Health</h1>
                    <p className="health-hero-sub">
                        Live status of every microservice in the NeXo operations stack.
                        Auto-refreshes every 15 seconds.
                    </p>
                    <div className="health-hero-meta">
                        <span className="health-chip" style={{ borderColor: overallColor, color: overallColor }}>
                            <span className="health-pulse" style={{ background: overallColor }} />
                            {overallLabel.toUpperCase()}
                        </span>
                        {data && (
                            <>
                                <span className="health-meta-item">
                                    <strong style={{ color: "var(--color-success)" }}>{data.up}</strong> up
                                </span>
                                <span className="health-meta-item">
                                    <strong style={{ color: data.down > 0 ? "var(--color-danger)" : "var(--text-muted)" }}>{data.down}</strong> down
                                </span>
                                {lastRefresh && (
                                    <span className="health-meta-item" style={{ color: "var(--text-muted)" }}>
                                        Checked {lastRefresh.toLocaleTimeString()}
                                    </span>
                                )}
                            </>
                        )}
                    </div>
                </div>
                <div className="health-hero-right">
                    <HealthRing value={healthPct} color={overallColor} />
                    <button className="btn btn-primary" onClick={load} disabled={loading}>
                        {loading ? "Refreshing…" : "Refresh now"}
                    </button>
                </div>
            </div>

            {/* Service grid */}
            <div className="health-grid">
                {(data?.services ?? Array.from({ length: 6 }).map((_, i) => ({
                    id: `skeleton-${i}`, name: "—", category: "api", port: 0,
                    status: "unknown" as const, latencyMs: null, statusCode: null,
                }) as ServiceCheck)).map((svc) => (
                    <ServiceCard key={svc.id} svc={svc} />
                ))}
            </div>

            {/* SigNoz embedded observability */}
            <SigNozEmbed signozStatus={data?.services.find(s => s.id === "signoz")?.status ?? "unknown"} />

            {/* Architecture strip */}
            <div className="card" style={{ padding: "20px 24px" }}>
                <div className="section-title">
                    <span className="dot"></span>
                    Stack Topology
                </div>
                <div className="health-topology">
                    <TopoNode label="Dashboard" sub=":3001 · Next.js" color="var(--brand-primary)" />
                    <TopoArrow />
                    <TopoNode label="API Gateway" sub=":8000 · FastAPI" color="var(--color-info)" />
                    <TopoArrow />
                    <TopoNode label="AI Service" sub=":8001 · scikit-learn" color="var(--color-purple)" />
                    <TopoArrow />
                    <TopoNode label="PostgreSQL" sub=":5432" color="var(--color-warning)" />
                </div>
                <div className="health-topology" style={{ marginTop: 12 }}>
                    <TopoNode label="Auth" sub=":8002 · JWT + OAuth" color="var(--brand-accent)" />
                    <TopoArrow />
                    <TopoNode label="Pipeline" sub="daemon · 2-min cycle" color="var(--color-success)" />
                    <TopoArrow />
                    <TopoNode label="MinIO" sub=":9000 · S3 data lake" color="var(--color-warning)" />
                </div>
            </div>

            {/* Quick links */}
            <div className="health-links">
                <QuickLink href="http://localhost:9001" title="MinIO Console" sub="Buckets · objects · policies" accent="var(--color-warning)" />
                <QuickLink href="http://localhost:8000/docs" title="API Swagger" sub="Interactive REST API explorer" accent="var(--color-info)" />
                <QuickLink href="http://localhost:8001/docs" title="AI Service Docs" sub="ML inference endpoints" accent="var(--color-purple)" />
                <QuickLink href="http://localhost:8002/docs" title="Auth Docs" sub="Signup · login · OAuth flows" accent="var(--brand-accent)" />
            </div>
        </div>
    );
}

function ServiceCard({ svc }: { svc: ServiceCheck }) {
    const meta = CATEGORY_META[svc.category];
    const statusColor =
        svc.status === "up" ? "var(--color-success)" :
            svc.status === "down" ? "var(--color-danger)" : "var(--text-muted)";
    const statusBg =
        svc.status === "up" ? "var(--color-success-bg)" :
            svc.status === "down" ? "var(--color-danger-bg)" : "var(--bg-elevated)";

    return (
        <div className="health-card" style={{ borderColor: statusColor }}>
            <div className="health-card-top">
                <div className="health-card-icon" style={{ background: `${meta.color}1A`, color: meta.color }}>
                    {meta.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="health-card-name">{svc.name}</div>
                    <div className="health-card-tag">{meta.label} · :{svc.port || "—"}</div>
                </div>
                <span className="health-card-status" style={{ background: statusBg, color: statusColor, borderColor: statusColor }}>
                    <span className="health-pulse" style={{ background: statusColor }} />
                    {svc.status.toUpperCase()}
                </span>
            </div>
            <div className="health-card-meta">
                <div>
                    <div className="health-card-label">Latency</div>
                    <div className="health-card-value">
                        {svc.latencyMs !== null ? `${svc.latencyMs} ms` : "—"}
                    </div>
                </div>
                <div>
                    <div className="health-card-label">HTTP</div>
                    <div className="health-card-value">{svc.statusCode ?? "—"}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                    <div className="health-card-label">Action</div>
                    {svc.publicUrl ? (
                        <a href={svc.publicUrl} target="_blank" rel="noreferrer" className="health-card-link">
                            Open ↗
                        </a>
                    ) : (
                        <span className="health-card-value" style={{ color: "var(--text-muted)" }}>internal</span>
                    )}
                </div>
            </div>
            {svc.error && (
                <div className="health-card-error">⚠ {svc.error}</div>
            )}
        </div>
    );
}

function HealthRing({ value, color }: { value: number; color: string }) {
    const r = 42;
    const c = 2 * Math.PI * r;
    const offset = c - (value / 100) * c;
    return (
        <div className="health-ring">
            <svg width="120" height="120" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
                <circle
                    cx="60" cy="60" r={r}
                    fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={c} strokeDashoffset={offset}
                    transform="rotate(-90 60 60)"
                    style={{ transition: "stroke-dashoffset 0.6s ease" }}
                />
            </svg>
            <div className="health-ring-label">
                <div style={{ fontSize: 26, fontWeight: 700, color }}>{value}%</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", letterSpacing: 0.5 }}>UPTIME</div>
            </div>
        </div>
    );
}

function TopoNode({ label, sub, color }: { label: string; sub: string; color: string }) {
    return (
        <div className="topo-node" style={{ borderColor: color }}>
            <div style={{ fontSize: 13, fontWeight: 600, color }}>{label}</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{sub}</div>
        </div>
    );
}

function TopoArrow() {
    return <div className="topo-arrow">→</div>;
}

function SigNozEmbed({ signozStatus }: { signozStatus: "up" | "down" | "unknown" }) {
    const isUp = signozStatus === "up";
    return (
        <div className="card card-accent-top signoz-panel">
            <div className="signoz-panel-header">
                <div>
                    <div className="section-title">
                        <span className="dot" style={{ background: isUp ? "var(--color-success)" : "var(--color-warning)" }}></span>
                        SigNoz Observability
                        <span className="signoz-panel-badge" style={{
                            background: isUp ? "var(--color-success-bg)" : "var(--color-warning-bg)",
                            color: isUp ? "var(--color-success)" : "var(--color-warning)",
                            borderColor: isUp ? "var(--color-success-border)" : "var(--color-warning-border)",
                        }}>
                            {isUp ? "LIVE" : "STARTING"}
                        </span>
                    </div>
                    <div className="signoz-panel-sub">
                        Traces · Metrics · Logs — collected via OpenTelemetry, stored in ClickHouse
                    </div>
                </div>
                <div className="signoz-panel-actions">
                    <a href="http://localhost:3301/services" target="_blank" rel="noreferrer" className="btn btn-ghost">Services →</a>
                    <a href="http://localhost:3301/traces-explorer" target="_blank" rel="noreferrer" className="btn btn-ghost">Traces →</a>
                    <a href="http://localhost:3301" target="_blank" rel="noreferrer" className="btn btn-primary">Open SigNoz ↗</a>
                </div>
            </div>

            {isUp ? (
                <div className="signoz-embed-wrap">
                    <iframe
                        className="signoz-embed"
                        src="http://localhost:3301"
                        title="SigNoz Observability Dashboard"
                        loading="lazy"
                    />
                </div>
            ) : (
                <div className="signoz-fallback">
                    <div className="signoz-fallback-icon">⏳</div>
                    <div className="signoz-fallback-title">SigNoz is starting up…</div>
                    <div className="signoz-fallback-sub">
                        First boot can take 30–60 seconds while ClickHouse initializes schemas.
                        Run <code>docker compose logs -f signoz-frontend</code> to follow progress.
                    </div>
                </div>
            )}

            <div className="signoz-stats-row">
                <div className="signoz-stat">
                    <div className="signoz-stat-label">OTLP gRPC</div>
                    <div className="signoz-stat-value">:4317</div>
                </div>
                <div className="signoz-stat">
                    <div className="signoz-stat-label">OTLP HTTP</div>
                    <div className="signoz-stat-value">:4318</div>
                </div>
                <div className="signoz-stat">
                    <div className="signoz-stat-label">UI</div>
                    <div className="signoz-stat-value">:3301</div>
                </div>
                <div className="signoz-stat">
                    <div className="signoz-stat-label">Storage</div>
                    <div className="signoz-stat-value">ClickHouse</div>
                </div>
            </div>
        </div>
    );
}

function QuickLink({ href, title, sub, accent }: { href: string; title: string; sub: string; accent: string }) {
    return (
        <a href={href} target="_blank" rel="noreferrer" className="quick-link" style={{ ["--accent" as any]: accent }}>
            <div className="quick-link-title">{title}</div>
            <div className="quick-link-sub">{sub}</div>
            <div className="quick-link-arrow">↗</div>
        </a>
    );
}
