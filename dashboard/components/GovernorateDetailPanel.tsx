"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    X, MapPin, AlertTriangle, Activity, ArrowRight, Clock, Sigma,
    Radio, TrendingDown, GitBranch, Info,
} from "lucide-react";
import type { GovernorateRow } from "../lib/tunisia-areas";
import { areaToGovernorate } from "../lib/tunisia-areas";

interface GrangerRow {
    area?: string;
    oss_variable: string;
    cem_variable: string;
    direction?: string;
    best_lag: number;
    best_pvalue: number;
    significant?: boolean;
}

interface CellRow {
    cell_id: string;
    area: string;
    total: number;
    anomaly_count: number;
    rate: number;
}

interface RecentAnomaly {
    cell_id: string;
    area: string;
    throughput_mbps: number;
    latency_ms: number;
    packet_loss_rate: number;
    cell_load_pct: number;
    timestamp: string;
}

interface Props {
    governorate: string | null;
    row: GovernorateRow | undefined;
    grangerAll: GrangerRow[];                  // full list, we filter to area
    cellsAll: CellRow[];                       // top cells from /api/vae-anomalies
    recentAll: RecentAnomaly[];                // recent flagged anomalies
    onClose: () => void;
}

/** Map KPI dimension → human cause copy used in tooltips. */
const OSS_CAUSE_COPY: Record<string, { title: string; reason: string }> = {
    throughput_mbps: {
        title: "Downlink throughput collapse",
        reason: "Sector congestion or backhaul bottleneck reduces per-user bitrate — VAE encodes this as elevated reconstruction error in the throughput input.",
    },
    latency_ms_derived: {
        title: "Latency spike",
        reason: "Queueing delay or upstream NAT congestion. Granger lag tells us how many cycles before CEM score drops follow.",
    },
    packet_loss_pct_derived: {
        title: "Packet loss",
        reason: "RF interference or transport-layer drop. Strongly Granger-causes CEM degradation 1–3 lags out.",
    },
    integrity: {
        title: "PDP integrity breach",
        reason: "Bearer setup failures — subscriber CANNOT establish data session. Direct CEM hit, often instant (lag=1).",
    },
    call_drop_rate: {
        title: "Call-drop rate exceeded threshold",
        reason: "Mobility / handover failure or coverage hole. Voice QoE collapse precedes data complaints by ~2 cycles.",
    },
    rsrp_dbm: {
        title: "RSRP below coverage floor",
        reason: "Cell-edge users dropping to 2G/3G fallback — RAT-underservice classifier picks them up downstream.",
    },
    cell_load_pct: {
        title: "Cell load saturation",
        reason: "Resource block utilization > 85% sustained — Granger-causes throughput drop, then CEM dip.",
    },
    jitter_ms_derived: {
        title: "Jitter excursion",
        reason: "Variable transport delay; affects VoLTE MOS and streaming buffer health.",
    },
    active_users: {
        title: "Concurrent user surge",
        reason: "Local event or daypart effect. Combined with cell_load, signals capacity-bound experience risk.",
    },
};

function pValueBadge(p: number): { label: string; cls: string } {
    if (p < 0.01) return { label: "p<0.01", cls: "badge-danger" };
    if (p < 0.05) return { label: "p<0.05", cls: "badge-warning" };
    if (p < 0.10) return { label: "p<0.10", cls: "badge-info" };
    return { label: `p=${p.toFixed(3)}`, cls: "badge-muted" };
}

export default function GovernorateDetailPanel({
    governorate,
    row,
    grangerAll,
    cellsAll,
    recentAll,
    onClose,
}: Props) {
    const [lagWindowMin, setLagWindowMin] = useState<number>(43200);

    // Fetch lag window from /granger-causality/explain (real config, no mock)
    useEffect(() => {
        if (!governorate) return;
        let cancel = false;
        (async () => {
            try {
                const r = await fetch("/api/granger-explain", { cache: "no-store" });
                if (!r.ok || cancel) return;
                const j = await r.json();
                if (j?.lag_window_minutes) setLagWindowMin(j.lag_window_minutes);
            } catch { /* keep default */ }
        })();
        return () => { cancel = true; };
    }, [governorate]);

    // Filter Granger pairs to this area. Granger rows have `area` from prod engine.
    // Some come back with raw cell-prefix; normalize via areaToGovernorate.
    const granger = useMemo(() => {
        if (!governorate) return [];
        return grangerAll
            .filter((g) => {
                const gov = areaToGovernorate(g.area ?? null);
                return gov === governorate;
            })
            .sort((a, b) => a.best_pvalue - b.best_pvalue)
            .slice(0, 6);
    }, [grangerAll, governorate]);

    // Top cells in this governorate
    const cells = useMemo(() => {
        if (!governorate) return [];
        return cellsAll
            .filter((c) => areaToGovernorate(c.area) === governorate)
            .slice(0, 8);
    }, [cellsAll, governorate]);

    // Recent anomalies in this governorate — surface the worst KPI per row
    const recent = useMemo(() => {
        if (!governorate) return [];
        return recentAll
            .filter((r) => areaToGovernorate(r.area) === governorate)
            .slice(0, 5)
            .map((r) => {
                // Worst dimension by normalized excess
                const candidates: { key: string; norm: number }[] = [
                    { key: "latency_ms_derived", norm: Math.min(1, r.latency_ms / 200) },
                    { key: "packet_loss_pct_derived", norm: Math.min(1, r.packet_loss_rate / 10) },
                    { key: "cell_load_pct", norm: Math.min(1, r.cell_load_pct / 100) },
                    { key: "throughput_mbps", norm: Math.max(0, 1 - r.throughput_mbps / 100) },
                ];
                candidates.sort((a, b) => b.norm - a.norm);
                return { ...r, worstKey: candidates[0].key, worstScore: candidates[0].norm };
            });
    }, [recentAll, governorate]);

    return (
        <AnimatePresence>
            {governorate && (
                <motion.aside
                    key="detail"
                    initial={{ x: 480, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 480, opacity: 0 }}
                    transition={{ type: "spring", stiffness: 260, damping: 32 }}
                    className="gov-detail-panel"
                >
                    <header className="gov-detail-header">
                        <div className="gov-detail-title">
                            <MapPin size={15} strokeWidth={2.4} />
                            <span>{governorate}</span>
                        </div>
                        <button type="button" className="gov-detail-close" onClick={onClose} aria-label="Close">
                            <X size={14} />
                        </button>
                    </header>

                    {/* ── Summary tiles ─────────────────────────────────────── */}
                    <section className="gov-detail-section">
                        <div className="gov-detail-tiles">
                            <div className="gov-detail-tile">
                                <AlertTriangle size={12} strokeWidth={2.4} />
                                <div>
                                    <div className="gov-detail-tile-value">{row?.anomaly_count.toLocaleString() ?? 0}</div>
                                    <div className="gov-detail-tile-label">VAE anomalies</div>
                                </div>
                            </div>
                            <div className="gov-detail-tile">
                                <Activity size={12} strokeWidth={2.4} />
                                <div>
                                    <div className="gov-detail-tile-value">{row?.rate?.toFixed(1) ?? "0.0"}%</div>
                                    <div className="gov-detail-tile-label">Anomaly rate</div>
                                </div>
                            </div>
                            <div className="gov-detail-tile">
                                <Radio size={12} strokeWidth={2.4} />
                                <div>
                                    <div className="gov-detail-tile-value">{row?.cell_count.toLocaleString() ?? 0}</div>
                                    <div className="gov-detail-tile-label">Cells observed</div>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* ── Granger causal pairs ──────────────────────────────── */}
                    <section className="gov-detail-section">
                        <div className="gov-detail-section-header">
                            <GitBranch size={13} strokeWidth={2.4} />
                            <h4>Causal pairs (Granger F-test)</h4>
                            <span className="gov-detail-section-meta">
                                {granger.length ? `${granger.length} significant` : "no pairs yet"}
                            </span>
                        </div>
                        <p className="gov-detail-section-help">
                            <Info size={11} strokeWidth={2.4} /> Past OSS values that statistically
                            predict CEM movement here. Lead time = best_lag × {lagWindowMin.toLocaleString()} min.
                        </p>
                        {granger.length === 0 ? (
                            <div className="gov-detail-empty">
                                No Granger-significant OSS→CEM pairs have accumulated for this
                                governorate yet. Pipeline needs more cycles.
                            </div>
                        ) : (
                            <ul className="gov-detail-pairs">
                                {granger.map((g, i) => {
                                    const cause = OSS_CAUSE_COPY[g.oss_variable];
                                    const leadMin = g.best_lag * lagWindowMin;
                                    const leadH = leadMin / 60;
                                    const pBadge = pValueBadge(g.best_pvalue);
                                    return (
                                        <li key={i} className="gov-detail-pair">
                                            <div className="gov-detail-pair-formula">
                                                <code className="gov-detail-pair-oss">{g.oss_variable}</code>
                                                <ArrowRight size={11} strokeWidth={2.4} />
                                                <code className="gov-detail-pair-cem">{g.cem_variable}</code>
                                                <span className={`badge ${pBadge.cls}`}>{pBadge.label}</span>
                                            </div>
                                            <div className="gov-detail-pair-meta">
                                                <span>
                                                    <Clock size={10} strokeWidth={2.4} />
                                                    lag={g.best_lag} (~{leadH < 1 ? `${leadMin.toFixed(0)} min` : `${leadH.toFixed(1)} h`})
                                                </span>
                                                <span>
                                                    <Sigma size={10} strokeWidth={2.4} />
                                                    p={g.best_pvalue.toFixed(4)}
                                                </span>
                                            </div>
                                            {cause && (
                                                <div className="gov-detail-pair-cause">
                                                    <strong>{cause.title}.</strong> {cause.reason}
                                                </div>
                                            )}
                                        </li>
                                    );
                                })}
                            </ul>
                        )}
                    </section>

                    {/* ── Worst KPI on recent anomalies ─────────────────────── */}
                    <section className="gov-detail-section">
                        <div className="gov-detail-section-header">
                            <TrendingDown size={13} strokeWidth={2.4} />
                            <h4>Top failure modes (recent VAE flags)</h4>
                        </div>
                        {recent.length === 0 ? (
                            <div className="gov-detail-empty">No recent anomalies in {governorate}.</div>
                        ) : (
                            <ul className="gov-detail-recent">
                                {recent.map((r, i) => {
                                    const cause = OSS_CAUSE_COPY[r.worstKey];
                                    return (
                                        <li key={i} className="gov-detail-recent-row">
                                            <div className="gov-detail-recent-meta">
                                                <code>{r.cell_id}</code>
                                                <span className="gov-detail-recent-time">
                                                    {new Date(r.timestamp).toLocaleTimeString()}
                                                </span>
                                            </div>
                                            <div className="gov-detail-recent-cause">
                                                {cause?.title ?? r.worstKey}
                                            </div>
                                            <div className="gov-detail-recent-kpis">
                                                <span>thr {r.throughput_mbps.toFixed(1)} Mbps</span>
                                                <span>lat {r.latency_ms.toFixed(0)} ms</span>
                                                <span>loss {(r.packet_loss_rate * 100).toFixed(2)}%</span>
                                                <span>load {r.cell_load_pct.toFixed(0)}%</span>
                                            </div>
                                        </li>
                                    );
                                })}
                            </ul>
                        )}
                    </section>

                    {/* ── Top affected cells ────────────────────────────────── */}
                    <section className="gov-detail-section">
                        <div className="gov-detail-section-header">
                            <Radio size={13} strokeWidth={2.4} />
                            <h4>Top affected cells</h4>
                            <span className="gov-detail-section-meta">{cells.length}</span>
                        </div>
                        {cells.length === 0 ? (
                            <div className="gov-detail-empty">No cells with anomalies above threshold.</div>
                        ) : (
                            <ul className="gov-detail-cells">
                                {cells.map((c, i) => (
                                    <li key={i} className="gov-detail-cell-row">
                                        <code>{c.cell_id}</code>
                                        <div className="gov-detail-cell-bar">
                                            <div
                                                className="gov-detail-cell-bar-fill"
                                                style={{ width: `${Math.min(100, c.rate * 5)}%` }}
                                            />
                                        </div>
                                        <span className="gov-detail-cell-val">
                                            {c.anomaly_count}/{c.total} ({c.rate.toFixed(1)}%)
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>
                </motion.aside>
            )}
        </AnimatePresence>
    );
}
