"use client";

import { useEffect, useState, useCallback } from "react";
import {
    Database, Layers, Network, MapPin, RadioTower, GitMerge,
    Cloud, Cpu, MessagesSquare, Workflow, ShieldCheck, RefreshCw,
} from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import StatTile from "../../components/ui/StatTile";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonStatCard } from "../../components/ui/LoadingSkeleton";
import { formatTunisDateTime } from "../../lib/time";

// ── Shapes mirror GET /data-lake/summary (honesty: any field may be null) ──
interface LayerStat { objects: number | null; bytes: number | null; }
interface Summary {
    sources: { oss_cell_kpis: number | null; bss_subscribers: number | null; subscriber_features: number | null } | null;
    last_ingest?: { oss: string | null; bss: string | null } | null;
    layers: Record<string, LayerStat> | null;
    twin: { governorates_spanned: number | null; oss_cells_monitored: number | null; convergence_pairs: number | null } | null;
    generated_at?: string;
    error?: string;
}

// '—' for any value the backend could not honestly compute.
const fmtNum = (n: number | null | undefined) =>
    n === null || n === undefined ? "—" : n.toLocaleString("en-US");

const fmtBytes = (b: number | null | undefined) => {
    if (b === null || b === undefined) return "—";
    if (b === 0) return "0 B";
    const u = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(b) / Math.log(1024));
    return `${(b / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${u[i]}`;
};

// Huawei "Converged Data & AI Solution for Autonomous Networks" → NeXo realisation.
// Each row is a blueprint capability mapped to the concrete artefact that proves it.
const BLUEPRINT: { icon: any; huawei: string; nexo: string; proof: string }[] = [
    { icon: Cloud, huawei: "Converged Data Lake (OceanStor / DLI)", nexo: "MinIO 3-layer lake — raw → processed → curated", proof: "Object counts + bytes below, all on-prem" },
    { icon: Network, huawei: "Spatio-Temporal Digital Twin", nexo: "NeXo Convergence Layer — WHERE (governorate geo-join) + WHEN (Granger lag)", proof: "Twin metrics below" },
    { icon: Cpu, huawei: "MIE + SRCON inference engines", nexo: "v3.0 models (CEM LightGBM · VAE · RAT XGBoost) + Granger causality", proof: "/model-evaluation · /granger-causality" },
    { icon: MessagesSquare, huawei: "DataChat natural-language ops", nexo: "L4 Agent chat (OpenRouter orchestrator → CEM/Network/Action agents)", proof: "/l4-agent" },
    { icon: Workflow, huawei: "Closed-loop self-healing", nexo: "L4 actuation — armed envelope auto-executes whitelisted playbooks", proof: "/l4-agent (Closed Loop)" },
    { icon: ShieldCheck, huawei: "Data sovereignty / on-prem deployment", nexo: "Entire lake + models run inside the local WSL/Docker host — no cloud egress", proof: "Confidential TT data never leaves host" },
];

export default function DataLakePage() {
    const [data, setData] = useState<Summary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const r = await fetch("/api/data-lake", { cache: "no-store" });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const json: Summary = await r.json();
            if (json.error && !json.sources) throw new Error(json.error);
            setData(json);
        } catch (e: any) {
            setError(String(e?.message ?? e));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const layers = data?.layers ?? {};
    const twin = data?.twin;
    const src = data?.sources;

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={Network}
                title="Converged Data Lake — Spatio-Temporal Convergence Layer"
                subtitle="OSS + BSS as one domain-scoped data lake, mapped to Huawei's Converged Data & AI blueprint. Every metric is a live count from the running stack."
                tone="default"
                action={
                    <button className="l4-btn" onClick={load} disabled={loading} title="Refresh">
                        <RefreshCw size={14} strokeWidth={2.2} />
                        <span>Refresh</span>
                    </button>
                }
            />

            {error && <ErrorState message={error} onRetry={load} />}

            {loading && !data ? (
                <div className="grid grid-3"><SkeletonStatCard /><SkeletonStatCard /><SkeletonStatCard /></div>
            ) : (
                <>
                    {/* ── Data sources (what feeds the lake) ─────────────── */}
                    <div className="grid grid-3">
                        <StatTile label="OSS Cell KPIs" value={fmtNum(src?.oss_cell_kpis)} icon={RadioTower}
                            tone="info" sub={data?.last_ingest?.oss ? `last ingest ${formatTunisDateTime(data.last_ingest.oss)}` : "real network telemetry"} />
                        <StatTile label="BSS Subscribers" value={fmtNum(src?.bss_subscribers)} icon={Database}
                            tone="info" sub={data?.last_ingest?.bss ? `last ingest ${formatTunisDateTime(data.last_ingest.bss)}` : "real + simulated CEM profiles"} />
                        <StatTile label="Subscriber Features" value={fmtNum(src?.subscriber_features)} icon={GitMerge}
                            tone="default" sub="engineered CEM feature rows" />
                    </div>

                    {/* ── Digital twin (the convergence layer) ───────────── */}
                    <SectionHeader icon={MapPin} title="Spatio-Temporal Digital Twin"
                        subtitle="WHERE the network lives (geographic breadth) and the joint O+B signal it produces." tone="success" />
                    <div className="grid grid-3">
                        <StatTile label="Governorates Spanned" value={fmtNum(twin?.governorates_spanned)} icon={MapPin}
                            tone="success" sub="WHERE — distinct BSS area buckets across Tunisia" />
                        <StatTile label="OSS Cells Monitored" value={fmtNum(twin?.oss_cells_monitored)} icon={RadioTower}
                            tone="success" sub="spatial granularity — distinct cell sites" />
                        <StatTile label="Convergence Pairs" value={fmtNum(twin?.convergence_pairs)} icon={GitMerge}
                            tone="success" sub="persisted O+B correlation rows" />
                    </div>

                    {/* ── MinIO 3-layer lake ─────────────────────────────── */}
                    <SectionHeader icon={Layers} title="3-Layer Data Lake (MinIO)"
                        subtitle="Raw landing → processed → curated. Object counts and footprint are live from the object store." tone="default" />
                    <div className="grid grid-3">
                        {["raw", "processed", "curated"].map((layer) => {
                            const s = (layers as Record<string, LayerStat>)[layer];
                            return (
                                <div key={layer} className="card" style={{ padding: 18 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                                        <Layers size={15} strokeWidth={2.2} style={{ color: "#007DBA" }} />
                                        <span style={{ fontWeight: 600, textTransform: "capitalize" }}>{layer}</span>
                                    </div>
                                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 6 }}>
                                        <span style={{ opacity: 0.7 }}>Objects</span>
                                        <strong>{fmtNum(s?.objects)}</strong>
                                    </div>
                                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                                        <span style={{ opacity: 0.7 }}>Footprint</span>
                                        <strong>{fmtBytes(s?.bytes)}</strong>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* ── Huawei → NeXo blueprint mapping ────────────────── */}
                    <SectionHeader icon={Cloud} title="Huawei Blueprint → NeXo Realisation"
                        subtitle="How this domain-scoped lake mirrors the Converged Data & AI Solution for Autonomous Networks." tone="default" />
                    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                        <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                            <thead>
                                <tr style={{ textAlign: "left", fontSize: 12, opacity: 0.7 }}>
                                    <th style={{ padding: "12px 16px" }}>Huawei capability</th>
                                    <th style={{ padding: "12px 16px" }}>NeXo realisation</th>
                                    <th style={{ padding: "12px 16px" }}>Evidence</th>
                                </tr>
                            </thead>
                            <tbody>
                                {BLUEPRINT.map((row, i) => {
                                    const Icon = row.icon;
                                    return (
                                        <tr key={i}>
                                            <td style={{ padding: "12px 16px", whiteSpace: "nowrap" }}>
                                                <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                                                    <Icon size={15} strokeWidth={2.2} style={{ color: "#007DBA", flexShrink: 0 }} />
                                                    {row.huawei}
                                                </span>
                                            </td>
                                            <td style={{ padding: "12px 16px", fontSize: 13 }}>{row.nexo}</td>
                                            <td style={{ padding: "12px 16px", fontSize: 12, opacity: 0.75 }}>{row.proof}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    {data?.generated_at && (
                        <div style={{ fontSize: 12, opacity: 0.55, textAlign: "right" }}>
                            snapshot generated {formatTunisDateTime(data.generated_at)} · cached 30s
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
