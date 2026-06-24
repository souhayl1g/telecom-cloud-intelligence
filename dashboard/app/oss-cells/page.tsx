"use client";

import { useEffect, useState, useCallback } from "react";
import { RadioTower, RefreshCw, AlertTriangle } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonTable } from "../../components/ui/LoadingSkeleton";

interface Cell {
    cell_id: string; area: string; rat_type: string; site_name: string;
    throughput_mbps: number; latency_ms: number; packet_loss_pct: number;
    cell_load_pct: number; integrity: number; call_drop_rate: number;
    rsrp_dbm: number; active_users: number; anomaly_flag: boolean; month_year: string;
}

const num = (v: number | null, d = 1) => (v === null || v === undefined ? "—" : v.toFixed(d));

export default function OssCellsPage() {
    const [rows, setRows] = useState<Cell[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [area, setArea] = useState("");
    const [rat, setRat] = useState("");
    const [anomalyOnly, setAnomalyOnly] = useState(false);

    const load = useCallback(async () => {
        setLoading(true); setError(null);
        const p = new URLSearchParams({ limit: "150" });
        if (area) p.set("area", area);
        if (rat) p.set("rat", rat);
        if (anomalyOnly) p.set("anomaly", "true");
        try {
            const r = await fetch(`/api/oss-cells?${p.toString()}`, { cache: "no-store" });
            const d = await r.json();
            if (d.error && !d.rows) throw new Error(d.error);
            setRows(d.rows ?? []);
        } catch (e: any) { setError(String(e?.message ?? e)); }
        finally { setLoading(false); }
    }, [area, rat, anomalyOnly]);

    useEffect(() => { load(); }, [load]);

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={RadioTower}
                title="OSS Cells"
                subtitle="Operational browser over cell KPIs (derived view). Filter by area, RAT, or anomalies. Anomalous cells surface first."
                tone="default"
                action={<button className="l4-btn" onClick={load} disabled={loading}><RefreshCw size={14} strokeWidth={2.2} /></button>}
            />

            <div className="card card-compact" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <input placeholder="area (e.g. 3G_Essijoumi)" value={area} onChange={(e) => setArea(e.target.value)}
                    style={inp} onKeyDown={(e) => e.key === "Enter" && load()} />
                <select value={rat} onChange={(e) => setRat(e.target.value)} style={inp}>
                    <option value="">all RAT</option><option>2G</option><option>3G</option><option>4G</option>
                </select>
                <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13 }}>
                    <input type="checkbox" checked={anomalyOnly} onChange={(e) => setAnomalyOnly(e.target.checked)} /> anomalies only
                </label>
                <button className="l4-btn l4-btn-approve" onClick={load}>Apply</button>
            </div>

            {error && <ErrorState message={error} onRetry={load} />}

            {loading ? <SkeletonTable rows={8} /> : (
                <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse", minWidth: 860 }}>
                        <thead>
                            <tr style={{ fontSize: 11, opacity: 0.75, textAlign: "left" }}>
                                <th style={th}>Cell</th><th style={th}>Area</th><th style={th}>RAT</th>
                                <th style={thr}>Thrpt</th><th style={thr}>Lat ms</th><th style={thr}>Loss%</th>
                                <th style={thr}>Load%</th><th style={thr}>Integ</th><th style={thr}>CDR</th><th style={thr}>Users</th><th style={th} />
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((c) => (
                                <tr key={c.cell_id} style={c.anomaly_flag ? { background: "rgba(220,38,38,0.07)" } : undefined}>
                                    <td style={{ ...td, fontFamily: "var(--font-mono, monospace)", fontSize: 11 }}>{c.cell_id}</td>
                                    <td style={td}>{c.area}</td>
                                    <td style={td}>{c.rat_type}</td>
                                    <td style={tdr}>{num(c.throughput_mbps)}</td>
                                    <td style={tdr}>{num(c.latency_ms)}</td>
                                    <td style={tdr}>{num(c.packet_loss_pct, 2)}</td>
                                    <td style={tdr}>{num(c.cell_load_pct)}</td>
                                    <td style={tdr}>{num(c.integrity)}</td>
                                    <td style={tdr}>{num(c.call_drop_rate, 2)}</td>
                                    <td style={tdr}>{c.active_users ?? "—"}</td>
                                    <td style={td}>{c.anomaly_flag && <AlertTriangle size={14} style={{ color: "#DC2626" }} />}</td>
                                </tr>
                            ))}
                            {rows.length === 0 && <tr><td colSpan={11} style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>No cells match.</td></tr>}
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
