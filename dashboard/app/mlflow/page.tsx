"use client";

import { useEffect, useState, useCallback } from "react";
import { FlaskConical, RefreshCw, ExternalLink, CheckCircle, Clock, XCircle, Tag } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import StatTile from "../../components/ui/StatTile";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonStatCard, SkeletonTable } from "../../components/ui/LoadingSkeleton";

interface Run {
    run_id: string;
    experiment_id: string | null;
    status: string | null;
    start_time: number | null;
    metrics: Record<string, number>;
    params: Record<string, string>;
}

interface ModelVersion { version: string; stage: string; status: string; }
interface RegisteredModel { name: string; creation_timestamp: number | null; latest_versions: ModelVersion[]; }
interface Experiment { experiment_id: string; name: string; lifecycle_stage: string; }

interface Summary {
    experiments: Experiment[];
    runs: Run[];
    registered_models: RegisteredModel[];
    mlflow_url: string;
    run_count: number;
    error?: string;
}

const stageTone = (s: string) =>
    s === "Production" ? "#10B981" : s === "Staging" ? "#F59E0B" : "#6B7280";

const statusIcon = (s: string | null) => {
    if (s === "FINISHED") return <CheckCircle size={13} color="#10B981" />;
    if (s === "FAILED") return <XCircle size={13} color="#DC2626" />;
    return <Clock size={13} color="#F59E0B" />;
};

const fmtTime = (ms: number | null) => {
    if (!ms) return "—";
    return new Date(ms).toLocaleString("en-GB", { timeZone: "Africa/Tunis", dateStyle: "short", timeStyle: "short" });
};

const fmtMetric = (v: number) => (Math.abs(v) < 0.001 || Math.abs(v) > 9999 ? v.toExponential(2) : v.toFixed(4));

export default function MlflowPage() {
    const [data, setData] = useState<Summary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true); setError(null);
        try {
            const r = await fetch("/api/mlflow", { cache: "no-store" });
            const d: Summary = await r.json();
            if (d.error && !d.run_count) throw new Error(d.error);
            setData(d);
        } catch (e: any) { setError(String(e?.message ?? e)); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    const mlflowUrl = data?.mlflow_url?.replace("mlflow", "localhost") ?? "http://localhost:5000";

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={FlaskConical}
                title="MLflow — Experiment Tracking & Model Registry"
                subtitle="Live view of training runs, metrics, and registered model versions. Backed by MinIO artifact store + PostgreSQL tracking DB."
                tone="default"
                action={
                    <div style={{ display: "flex", gap: 8 }}>
                        <a href={mlflowUrl} target="_blank" rel="noreferrer"
                            style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13,
                                padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)",
                                textDecoration: "none", color: "inherit", opacity: 0.85 }}>
                            <ExternalLink size={13} /> Full MLflow UI
                        </a>
                        <button className="l4-btn" onClick={load} disabled={loading} title="Refresh">
                            <RefreshCw size={14} strokeWidth={2.2} />
                            <span>Refresh</span>
                        </button>
                    </div>
                }
            />

            {error && <ErrorState message={error} onRetry={load} />}

            {/* ── Summary tiles ────────────────────────────────── */}
            {loading && !data ? (
                <div className="grid grid-3">
                    <SkeletonStatCard /><SkeletonStatCard /><SkeletonStatCard />
                </div>
            ) : (
                <div className="grid grid-3">
                    <StatTile label="Experiments" value={String(data?.experiments.length ?? "—")}
                        icon={FlaskConical} tone="info" sub="tracked experiment groups" />
                    <StatTile label="Training Runs" value={String(data?.run_count ?? "—")}
                        icon={Clock} tone="default" sub="logged runs (last 20 shown)" />
                    <StatTile label="Registered Models" value={String(data?.registered_models.length ?? "—")}
                        icon={Tag} tone="success" sub="models in registry" />
                </div>
            )}

            {/* ── Registered Model Registry ─────────────────────── */}
            {!loading && (data?.registered_models.length ?? 0) > 0 && (
                <>
                    <SectionHeader icon={Tag} title="Model Registry" tone="success"
                        subtitle="Registered models with version lifecycle stages (None → Staging → Production)." />
                    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                        <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                            <thead>
                                <tr style={{ fontSize: 11, opacity: 0.7, textAlign: "left" }}>
                                    <th style={{ padding: "10px 16px" }}>Model</th>
                                    <th style={{ padding: "10px 16px" }}>Versions</th>
                                    <th style={{ padding: "10px 16px" }}>Stages</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data!.registered_models.map((m) => (
                                    <tr key={m.name}>
                                        <td style={{ padding: "10px 16px", fontWeight: 600, fontSize: 13 }}>{m.name}</td>
                                        <td style={{ padding: "10px 16px", fontSize: 12 }}>
                                            {m.latest_versions.map(v => (
                                                <span key={v.version} style={{ marginRight: 8, fontFamily: "monospace" }}>
                                                    v{v.version}
                                                </span>
                                            ))}
                                            {m.latest_versions.length === 0 && "—"}
                                        </td>
                                        <td style={{ padding: "10px 16px" }}>
                                            {m.latest_versions.map(v => (
                                                <span key={v.version} style={{
                                                    display: "inline-block", marginRight: 8, fontSize: 11,
                                                    padding: "2px 8px", borderRadius: 10,
                                                    background: `${stageTone(v.stage)}22`,
                                                    color: stageTone(v.stage), fontWeight: 600,
                                                }}>
                                                    {v.stage || "None"}
                                                </span>
                                            ))}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            {/* ── Recent runs ───────────────────────────────────── */}
            <SectionHeader icon={Clock} title="Recent Training Runs"
                subtitle="Last 20 runs across all experiments, ordered by start time. Metrics logged via mlflow autolog()." tone="default" />

            {loading ? <SkeletonTable rows={6} /> : (data?.runs.length ?? 0) === 0 ? (
                <div className="card" style={{ padding: 24, textAlign: "center", opacity: 0.6, fontSize: 14 }}>
                    No runs logged yet. Run a training notebook and call{" "}
                    <code style={{ fontFamily: "monospace" }}>mlflow.autolog()</code> to see runs here.
                </div>
            ) : (
                <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse", minWidth: 700 }}>
                        <thead>
                            <tr style={{ fontSize: 11, opacity: 0.7, textAlign: "left" }}>
                                <th style={{ padding: "10px 14px" }}>Run</th>
                                <th style={{ padding: "10px 14px" }}>Status</th>
                                <th style={{ padding: "10px 14px" }}>Started</th>
                                <th style={{ padding: "10px 14px" }}>Key Metrics</th>
                                <th style={{ padding: "10px 14px" }}>Params</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data!.runs.map((r) => (
                                <tr key={r.run_id}>
                                    <td style={{ padding: "10px 14px", fontFamily: "monospace", fontSize: 12 }}>
                                        {r.run_id}
                                    </td>
                                    <td style={{ padding: "10px 14px" }}>
                                        <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12 }}>
                                            {statusIcon(r.status)} {r.status ?? "—"}
                                        </span>
                                    </td>
                                    <td style={{ padding: "10px 14px", fontSize: 12 }}>{fmtTime(r.start_time)}</td>
                                    <td style={{ padding: "10px 14px", fontSize: 11 }}>
                                        {Object.entries(r.metrics).slice(0, 3).map(([k, v]) => (
                                            <span key={k} style={{ display: "inline-block", marginRight: 10 }}>
                                                <span style={{ opacity: 0.65 }}>{k}: </span>
                                                <strong>{fmtMetric(v)}</strong>
                                            </span>
                                        ))}
                                        {Object.keys(r.metrics).length === 0 && <span style={{ opacity: 0.5 }}>—</span>}
                                    </td>
                                    <td style={{ padding: "10px 14px", fontSize: 11 }}>
                                        {Object.entries(r.params).slice(0, 2).map(([k, v]) => (
                                            <span key={k} style={{ display: "inline-block", marginRight: 10, opacity: 0.75 }}>
                                                {k}={v}
                                            </span>
                                        ))}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* ── Experiments ───────────────────────────────────── */}
            {!loading && (data?.experiments.length ?? 0) > 0 && (
                <>
                    <SectionHeader icon={FlaskConical} title="Experiments" tone="default"
                        subtitle="MLflow experiment groups. Each experiment holds runs for one model or hypothesis." />
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                        {data!.experiments.map((e) => (
                            <div key={e.experiment_id} className="card" style={{
                                padding: "10px 16px", display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13,
                            }}>
                                <FlaskConical size={14} style={{ color: "#007DBA" }} />
                                <span style={{ fontWeight: 600 }}>{e.name}</span>
                                <span style={{ fontSize: 11, opacity: 0.55 }}>#{e.experiment_id}</span>
                                <span style={{
                                    fontSize: 10, padding: "1px 6px", borderRadius: 8,
                                    background: e.lifecycle_stage === "active" ? "#10B98122" : "#DC262622",
                                    color: e.lifecycle_stage === "active" ? "#10B981" : "#DC2626",
                                }}>{e.lifecycle_stage}</span>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}
