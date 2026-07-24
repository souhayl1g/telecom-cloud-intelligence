"use client";

import { useEffect, useState, useCallback } from "react";
import { Users, RefreshCw } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonTable } from "../../components/ui/LoadingSkeleton";

interface Sub {
    imsi_hash: string; cem_score: number; rat_gap_score: number;
    network_experience_index: number; churn_risk_flag: boolean;
    month_year: string; area: string | null; usertype: string | null; highest_rat: string | null;
}

const num = (v: number | null, d = 3) => (v === null || v === undefined ? "—" : v.toFixed(d));
const cemTone = (s: number) => (s < 0.3 ? "#DC2626" : s < 0.6 ? "#F59E0B" : "#10B981");

export default function BssSubscribersPage() {
    const [rows, setRows] = useState<Sub[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [month, setMonth] = useState("");
    const [cemScore, setCemScore] = useState("");
    const [churnOnly, setChurnOnly] = useState(false);

    const load = useCallback(async () => {
        setLoading(true); setError(null);
        const p = new URLSearchParams({ limit: "150" });
        if (month) p.set("month", month);
        // Exact-ish CEM match: treat the typed precision as a rounding band, so
        // "0.7" -> [0.65,0.75), "0.70" -> [0.695,0.705). Sends min_cem+max_cem
        // (both already supported by the gateway) instead of an open-ended max.
        const v = parseFloat(cemScore);
        if (cemScore.trim() && !Number.isNaN(v)) {
            const decimals = Math.max((cemScore.split(".")[1] || "").length, 1);
            const half = 0.5 * Math.pow(10, -decimals);
            p.set("min_cem", Math.max(0, v - half).toFixed(4));
            p.set("max_cem", (v + half).toFixed(4));
        }
        if (churnOnly) p.set("churn", "true");
        try {
            const r = await fetch(`/api/bss-subscribers?${p.toString()}`, { cache: "no-store" });
            const d = await r.json();
            if (d.error && !d.rows) throw new Error(d.error);
            setRows(d.rows ?? []);
        } catch (e: any) { setError(String(e?.message ?? e)); }
        finally { setLoading(false); }
    }, [month, cemScore, churnOnly]);

    useEffect(() => { load(); }, [load]);

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={Users}
                title="BSS Subscribers"
                subtitle="Operational browser over subscriber experience (CEM, RAT-gap, churn). Newest first; unscored rows hidden. Type a CEM score to filter. imsi is hashed; aggregates only."
                tone="default"
                action={<button className="l4-btn" onClick={load} disabled={loading}><RefreshCw size={14} strokeWidth={2.2} /></button>}
            />

            <div className="card card-compact" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <input placeholder="month (e.g. 2026-03)" value={month} onChange={(e) => setMonth(e.target.value)} style={inp} onKeyDown={(e) => e.key === "Enter" && load()} />
                <input placeholder="CEM score (e.g. 0.7)" value={cemScore} onChange={(e) => setCemScore(e.target.value)} style={inp} onKeyDown={(e) => e.key === "Enter" && load()} />
                <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13 }}>
                    <input type="checkbox" checked={churnOnly} onChange={(e) => setChurnOnly(e.target.checked)} /> churn-risk only
                </label>
                <button className="l4-btn l4-btn-approve" onClick={load}>Apply</button>
            </div>

            {error && <ErrorState message={error} onRetry={load} />}

            {loading ? <SkeletonTable rows={8} /> : (
                <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse", minWidth: 760 }}>
                        <thead>
                            <tr style={{ fontSize: 11, opacity: 0.75, textAlign: "left" }}>
                                <th style={th}>IMSI (hash)</th><th style={th}>Area</th><th style={th}>User type</th><th style={th}>RAT</th>
                                <th style={thr}>CEM</th><th style={thr}>RAT-gap</th><th style={thr}>NEI</th><th style={th}>Churn</th><th style={th}>Month</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((s) => (
                                <tr key={s.imsi_hash + s.month_year}>
                                    <td style={{ ...td, fontFamily: "var(--font-mono, monospace)", fontSize: 11 }}>{s.imsi_hash.slice(0, 12)}…</td>
                                    <td style={td}>{s.area ?? "—"}</td>
                                    <td style={td}>{s.usertype ?? "—"}</td>
                                    <td style={td}>{s.highest_rat ?? "—"}</td>
                                    <td style={{ ...tdr, color: cemTone(s.cem_score), fontWeight: 700 }}>{num(s.cem_score)}</td>
                                    <td style={tdr}>{num(s.rat_gap_score)}</td>
                                    <td style={tdr}>{num(s.network_experience_index)}</td>
                                    <td style={td}>{s.churn_risk_flag ? <span style={{ color: "#DC2626", fontWeight: 700 }}>● risk</span> : "—"}</td>
                                    <td style={{ ...td, fontSize: 12, color: "var(--text-muted)" }}>{s.month_year}</td>
                                </tr>
                            ))}
                            {rows.length === 0 && <tr><td colSpan={9} style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>No subscribers match.</td></tr>}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

const inp: React.CSSProperties = { padding: "8px 10px", borderRadius: 8, fontSize: 13, background: "var(--glass-bg, rgba(255,255,255,0.04))", border: "1px solid var(--glass-border, rgba(255,255,255,0.12))", color: "inherit" };
const th: React.CSSProperties = { padding: "10px 12px" };
const thr: React.CSSProperties = { padding: "10px 12px", textAlign: "right" };
const td: React.CSSProperties = { padding: "8px 12px" };
const tdr: React.CSSProperties = { padding: "8px 12px", textAlign: "right", fontFamily: "var(--font-mono, monospace)", fontSize: 12 };
