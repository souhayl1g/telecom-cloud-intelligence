"use client";

import { useEffect, useState, useCallback } from "react";
import { Activity, RefreshCw, Server } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import StatTile from "../../components/ui/StatTile";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonStatCard } from "../../components/ui/LoadingSkeleton";
import { formatTunisDateTime } from "../../lib/time";

interface Point { t: number; v: number; }
interface Panel { key: string; label: string; unit: string; series: Point[] | null; }
interface Metrics {
    panels: Panel[] | null;
    targets?: { up: number | null; total: number | null };
    window_minutes?: number;
    generated_at?: string;
    error?: string;
}

// Minimal dependency-free sparkline (matches the project's "all charts custom SVG" rule).
function Spark({ series, unit }: { series: Point[] | null; unit: string }) {
    if (!series || series.length === 0) {
        return <div style={{ height: 60, display: "flex", alignItems: "center", color: "var(--text-muted)" }}>—</div>;
    }
    const w = 280, h = 60, pad = 4;
    const vals = series.map((p) => p.v);
    const min = Math.min(...vals), max = Math.max(...vals);
    const span = max - min || 1;
    const pts = series.map((p, i) => {
        const x = pad + (i / (series.length - 1)) * (w - 2 * pad);
        const y = h - pad - ((p.v - min) / span) * (h - 2 * pad);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    const last = vals[vals.length - 1];
    return (
        <div>
            <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: "block" }}>
                <polyline points={pts} fill="none" stroke="var(--brand-primary, #007DBA)" strokeWidth="2" />
            </svg>
            <div style={{ fontFamily: "var(--font-mono, monospace)", fontSize: 16, fontWeight: 700 }}>
                {last < 0.01 ? last.toExponential(2) : last.toFixed(3)} <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{unit}</span>
            </div>
        </div>
    );
}

export default function MetricsPage() {
    const [data, setData] = useState<Metrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true); setError(null);
        try {
            const r = await fetch("/api/metrics?minutes=30", { cache: "no-store" });
            const json: Metrics = await r.json();
            if (json.error && !json.panels) throw new Error(json.error);
            setData(json);
        } catch (e: any) { setError(String(e?.message ?? e)); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={Activity}
                title="System Metrics"
                subtitle="Live Prometheus telemetry rendered natively in-dashboard — no external Grafana. Trailing 30 min."
                tone="default"
                action={<button className="l4-btn" onClick={load} disabled={loading}><RefreshCw size={14} strokeWidth={2.2} /></button>}
            />

            {error && <ErrorState message={error} onRetry={load} />}

            <div className="grid grid-2">
                <StatTile label="Scrape targets up" icon={Server} tone={data?.targets?.up === data?.targets?.total ? "success" : "warning"}
                    value={data?.targets?.up != null && data?.targets?.total != null ? `${data.targets.up} / ${data.targets.total}` : "—"}
                    sub="Prometheus active targets" />
                <StatTile label="Window" value={`${data?.window_minutes ?? 30} min`} sub="trailing range" />
            </div>

            {loading && !data ? (
                <div className="grid grid-2"><SkeletonStatCard /><SkeletonStatCard /></div>
            ) : (
                <div className="grid grid-2">
                    {(data?.panels ?? []).map((p) => (
                        <div key={p.key} className="card" style={{ padding: 18 }}>
                            <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 8 }}>
                                {p.label}
                            </div>
                            <Spark series={p.series} unit={p.unit} />
                        </div>
                    ))}
                </div>
            )}

            {data?.generated_at && (
                <div style={{ fontSize: 12, opacity: 0.55, textAlign: "right" }}>
                    sampled {formatTunisDateTime(data.generated_at)} · source: Prometheus
                </div>
            )}
        </div>
    );
}
