"use client";

import { useEffect, useState, useCallback } from "react";
import { Table2, RefreshCw } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonStatCard } from "../../components/ui/LoadingSkeleton";

interface Stats { lo: number; hi: number; mean: number; med: number; n: number; }
interface Feature { column: string; stats: Stats | null; histogram: number[] | null; bin_lo?: number; bin_hi?: number; }
interface Summary { source: string; table: string; bins: number; features: Feature[] | null; error?: string; }

const fmt = (v: number | null | undefined) => {
    if (v === null || v === undefined) return "—";
    if (Math.abs(v) >= 1e6) return v.toExponential(2);
    return v.toFixed(Math.abs(v) < 1 ? 4 : 2);
};

// Dependency-free histogram bars.
function Histogram({ bins }: { bins: number[] | null }) {
    if (!bins || bins.length === 0) return <div style={{ color: "var(--text-muted)" }}>—</div>;
    const max = Math.max(...bins) || 1;
    return (
        <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 90 }}>
            {bins.map((c, i) => (
                <div key={i} title={`${c}`} style={{
                    flex: 1, height: `${(c / max) * 100}%`, minHeight: c > 0 ? 2 : 0,
                    background: "var(--brand-primary, #007DBA)", borderRadius: "2px 2px 0 0", opacity: 0.85,
                }} />
            ))}
        </div>
    );
}

export default function DataExplorerPage() {
    const [source, setSource] = useState<"bss" | "oss">("bss");
    const [data, setData] = useState<Summary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async (src: string) => {
        setLoading(true); setError(null);
        try {
            const r = await fetch(`/api/explorer?source=${src}`, { cache: "no-store" });
            const json: Summary = await r.json();
            if (json.error && !json.features) throw new Error(json.error);
            setData(json);
        } catch (e: any) { setError(String(e?.message ?? e)); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(source); }, [load, source]);

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={Table2}
                title="Data Explorer"
                subtitle="Honest EDA — feature distributions + stats over the curated tables, on a block sample. Aggregates only, no raw rows."
                tone="default"
                action={
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <div style={{ display: "flex", gap: 4 }}>
                            {(["bss", "oss"] as const).map((s) => (
                                <button key={s} className={`l4-btn ${source === s ? "l4-btn-approve" : ""}`} onClick={() => setSource(s)}>
                                    {s.toUpperCase()}
                                </button>
                            ))}
                        </div>
                        <button className="l4-btn" onClick={() => load(source)} disabled={loading}><RefreshCw size={14} strokeWidth={2.2} /></button>
                    </div>
                }
            />
            {data?.table && <div style={{ fontSize: 12, color: "var(--text-muted)" }}>source table: <code>{data.table}</code></div>}

            {error && <ErrorState message={error} onRetry={() => load(source)} />}

            {loading && !data ? <div className="grid grid-2"><SkeletonStatCard /><SkeletonStatCard /></div> : (
                <div className="grid grid-2">
                    {(data?.features ?? []).map((f) => (
                        <div key={f.column} className="card" style={{ padding: 18 }}>
                            <div style={{ fontWeight: 600, marginBottom: 4 }}>{f.column}</div>
                            <Histogram bins={f.histogram} />
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>
                                <span>{fmt(f.bin_lo)}</span><span>{fmt(f.bin_hi)}</span>
                            </div>
                            <div style={{ display: "flex", gap: 14, fontSize: 12, marginTop: 8, flexWrap: "wrap" }}>
                                <span>mean <strong>{fmt(f.stats?.mean)}</strong></span>
                                <span>median <strong>{fmt(f.stats?.med)}</strong></span>
                                <span>min <strong>{fmt(f.stats?.lo)}</strong></span>
                                <span>max <strong>{fmt(f.stats?.hi)}</strong></span>
                                <span>n <strong>{f.stats?.n?.toLocaleString() ?? "—"}</strong></span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
