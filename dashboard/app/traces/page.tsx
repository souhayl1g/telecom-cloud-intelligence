"use client";

import { useEffect, useState, useCallback } from "react";
import { GitBranch, RefreshCw } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonTable } from "../../components/ui/LoadingSkeleton";

interface Trace {
    trace_id: string;
    service: string;
    operation: string;
    span_count: number;
    duration_us: number;
    start_us: number;
}

const fmtDur = (us: number) => (us >= 1000 ? `${(us / 1000).toFixed(1)} ms` : `${us} µs`);
const fmtStart = (us: number) => new Date(us / 1000).toLocaleTimeString("en-GB", { timeZone: "Africa/Tunis" });

export default function TracesPage() {
    const [services, setServices] = useState<string[]>([]);
    const [service, setService] = useState("api-gateway");
    const [traces, setTraces] = useState<Trace[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // service dropdown
    useEffect(() => {
        fetch("/api/traces?list=services", { cache: "no-store" })
            .then((r) => r.json())
            .then((d) => { if (Array.isArray(d.services) && d.services.length) { setServices(d.services); setService(d.services[0]); } })
            .catch(() => {});
    }, []);

    const load = useCallback(async (svc: string) => {
        setLoading(true); setError(null);
        try {
            const r = await fetch(`/api/traces?service=${encodeURIComponent(svc)}&limit=30`, { cache: "no-store" });
            const d = await r.json();
            if (d.error && !d.traces) throw new Error(d.error);
            setTraces(d.traces ?? []);
        } catch (e: any) { setError(String(e?.message ?? e)); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(service); }, [load, service]);

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={GitBranch}
                title="Distributed Traces"
                subtitle="Live OpenTelemetry traces from Jaeger, rendered natively in-dashboard — no external Jaeger UI."
                tone="default"
                action={
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <select value={service} onChange={(e) => setService(e.target.value)}
                            style={{ padding: "6px 10px", borderRadius: 8, fontSize: 13, background: "var(--glass-bg, rgba(255,255,255,0.04))", border: "1px solid var(--glass-border, rgba(255,255,255,0.12))", color: "inherit" }}>
                            {(services.length ? services : [service]).map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                        <button className="l4-btn" onClick={() => load(service)} disabled={loading}><RefreshCw size={14} strokeWidth={2.2} /></button>
                    </div>
                }
            />

            {error && <ErrorState message={error} onRetry={() => load(service)} />}

            {loading ? <SkeletonTable rows={6} /> : (
                <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse", minWidth: 640 }}>
                        <thead>
                            <tr style={{ fontSize: 12, opacity: 0.75, textAlign: "left" }}>
                                <th style={{ padding: "12px 16px" }}>Operation</th>
                                <th style={{ padding: "12px 16px" }}>Service</th>
                                <th style={{ padding: "12px 16px", textAlign: "right" }}>Spans</th>
                                <th style={{ padding: "12px 16px", textAlign: "right" }}>Duration</th>
                                <th style={{ padding: "12px 16px", textAlign: "right" }}>Started</th>
                            </tr>
                        </thead>
                        <tbody>
                            {traces.map((t) => (
                                <tr key={t.trace_id} title={t.trace_id}>
                                    <td style={{ padding: "10px 16px", fontWeight: 600 }}>{t.operation}</td>
                                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-muted)" }}>{t.service}</td>
                                    <td style={{ padding: "10px 16px", textAlign: "right", fontFamily: "var(--font-mono, monospace)" }}>{t.span_count}</td>
                                    <td style={{ padding: "10px 16px", textAlign: "right", fontFamily: "var(--font-mono, monospace)" }}>{fmtDur(t.duration_us)}</td>
                                    <td style={{ padding: "10px 16px", textAlign: "right", fontSize: 12, color: "var(--text-muted)" }}>{fmtStart(t.start_us)}</td>
                                </tr>
                            ))}
                            {traces.length === 0 && (
                                <tr><td colSpan={5} style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)" }}>No traces for this service yet.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
