"use client";

import { useEffect, useState, useCallback } from "react";
import { Activity, RefreshCw, Info } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonStatCard } from "../../components/ui/LoadingSkeleton";
import { formatTunisDateTime } from "../../lib/time";

interface Cell { month: string; psi: number | null; ks: number | null; n: number; verdict: string | null; }
interface Feature { feature: string; label?: string; months: Cell[]; n_baseline: number; }
interface Summary {
    baseline: string;
    features: Feature[] | null;
    thresholds?: { stable: number; significant: number };
    generated_at?: string;
    error?: string;
}

// PSI → colour. Standard thresholds: <0.1 stable, 0.1–0.25 moderate, >0.25 significant.
function psiTone(psi: number | null): { bg: string; fg: string } {
    if (psi === null) return { bg: "transparent", fg: "var(--text-muted)" };
    if (psi < 0.1) return { bg: "rgba(16,185,129,0.16)", fg: "#10B981" };
    if (psi < 0.25) return { bg: "rgba(245,158,11,0.18)", fg: "#F59E0B" };
    return { bg: "rgba(220,38,38,0.20)", fg: "#DC2626" };
}

const fmt = (v: number | null) => (v === null || v === undefined ? "—" : v.toFixed(3));

const BASELINES = ["2026-01", "2026-02", "2026-03"];

export default function DataDriftPage() {
    const [data, setData] = useState<Summary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [baseline, setBaseline] = useState("2026-01");

    const load = useCallback(async (bl: string) => {
        setLoading(true);
        setError(null);
        try {
            const r = await fetch(`/api/drift?baseline=${bl}`, { cache: "no-store" });
            const json: Summary = await r.json();
            if (json.error && !json.features) throw new Error(json.error);
            setData(json);
        } catch (e: any) {
            setError(String(e?.message ?? e));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(baseline); }, [load, baseline]);

    // Column months = union across features (they share the monthly snapshots).
    const months = data?.features?.[0]?.months.map((m) => m.month) ?? [];

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={Activity}
                title="Data Drift Monitor"
                subtitle="Population Stability Index (PSI) of model features across monthly snapshots vs a baseline. Real computed values; '—' where a distribution is too degenerate to score."
                tone="default"
                action={
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <label style={{ fontSize: 12, color: "var(--text-muted)" }}>Baseline</label>
                        <select value={baseline} onChange={(e) => setBaseline(e.target.value)}
                            style={{ padding: "6px 10px", borderRadius: 8, background: "var(--glass-bg, rgba(255,255,255,0.04))",
                                border: "1px solid var(--glass-border, rgba(255,255,255,0.12))", color: "inherit", fontSize: 13 }}>
                            {BASELINES.map((b) => <option key={b} value={b}>{b}</option>)}
                        </select>
                        <button className="l4-btn" onClick={() => load(baseline)} disabled={loading} title="Refresh">
                            <RefreshCw size={14} strokeWidth={2.2} />
                        </button>
                    </div>
                }
            />

            {/* Legend */}
            <div className="card card-compact" style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap", fontSize: 12 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}><Info size={13} /> PSI thresholds:</span>
                <span style={{ color: "#10B981" }}>● &lt; 0.10 stable</span>
                <span style={{ color: "#F59E0B" }}>● 0.10–0.25 moderate drift</span>
                <span style={{ color: "#DC2626" }}>● &gt; 0.25 significant drift</span>
            </div>

            {error && <ErrorState message={error} onRetry={() => load(baseline)} />}

            {loading && !data ? (
                <div className="grid grid-3"><SkeletonStatCard /><SkeletonStatCard /><SkeletonStatCard /></div>
            ) : (
                <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
                        <thead>
                            <tr style={{ fontSize: 12, opacity: 0.75, textAlign: "left" }}>
                                <th style={{ padding: "12px 16px", position: "sticky", left: 0 }}>Feature</th>
                                {months.map((m) => (
                                    <th key={m} style={{ padding: "12px 12px", textAlign: "center", fontWeight: 600 }}>
                                        {m}{m === baseline ? " (base)" : ""}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {(data?.features ?? []).map((f) => (
                                <tr key={f.feature}>
                                    <td style={{ padding: "10px 16px", fontWeight: 600, whiteSpace: "nowrap" }}>
                                        {f.label ?? f.feature}
                                        <div style={{ fontSize: 10, color: "var(--text-muted)" }}>n={f.n_baseline.toLocaleString()}</div>
                                    </td>
                                    {f.months.map((c) => {
                                        const tone = psiTone(c.psi);
                                        return (
                                            <td key={c.month} title={c.psi !== null ? `PSI ${fmt(c.psi)} · KS ${fmt(c.ks)} · n=${c.n}` : "not scoreable"}
                                                style={{ padding: "8px 10px", textAlign: "center", background: tone.bg }}>
                                                <span style={{ color: tone.fg, fontWeight: 700, fontFamily: "var(--font-mono, monospace)", fontSize: 13 }}>
                                                    {fmt(c.psi)}
                                                </span>
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {data?.generated_at && (
                <div style={{ fontSize: 12, opacity: 0.55, textAlign: "right" }}>
                    computed {formatTunisDateTime(data.generated_at)} · cached 5 min · hover a cell for PSI/KS/n
                </div>
            )}
        </div>
    );
}
