"use client";
import { useEffect, useState, useCallback } from 'react';
import PageInfoBar from '../../components/PageInfoBar';

/* ── Types ──────────────────────────────────────────────────────────────── */
interface VAEData {
    summary: { total: number; anomaly_count: number; anomaly_rate: number; avg_cell_load_anomalous: number };
    byArea: { area: string; total: number; anomaly_count: number; rate: number }[];
    byCell: { cell_id: string; area: string; total: number; anomaly_count: number; rate: number }[];
    recentAnomalies: { cell_id: string; area: string; throughput_mbps: number; latency_ms: number; packet_loss_rate: number; cell_load_pct: number; timestamp: string }[];
    reconstructionError: { bin: string; normal: number; anomaly: number }[];
    threshold: number;
}

/* ── Stacked Bar Chart ──────────────────────────────────────────────────── */
function StackedBarChart({ data }: { data: { bin: string; normal: number; anomaly: number }[] }) {
    const maxTotal = Math.max(...data.map(d => d.normal + d.anomaly), 1);
    const barWidth = 24;
    const gap = 4;
    const totalWidth = data.length * (barWidth + gap);
    const height = 180;

    return (
        <svg width="100%" height={height} viewBox={`0 0 ${totalWidth} ${height}`} preserveAspectRatio="xMidYMid meet">
            {data.map((d, i) => {
                const total = d.normal + d.anomaly;
                const barHeight = (total / maxTotal) * 140;
                const normalHeight = (d.normal / maxTotal) * 140;
                const x = i * (barWidth + gap);

                return (
                    <g key={i}>
                        <rect
                            x={x}
                            y={height - 24 - barHeight}
                            width={barWidth}
                            height={barHeight}
                            fill="var(--color-danger)"
                            opacity={0.9}
                            rx={2}
                        />
                        <rect
                            x={x}
                            y={height - 24 - normalHeight}
                            width={barWidth}
                            height={normalHeight}
                            fill="var(--color-success)"
                            opacity={0.85}
                            rx={2}
                        />
                        <text
                            x={x + barWidth / 2}
                            y={height - 6}
                            textAnchor="middle"
                            style={{ fontSize: 7, fill: 'var(--text-muted)' }}
                        >
                            {d.bin}
                        </text>
                    </g>
                );
            })}
        </svg>
    );
}

/* ── Simple Bar Chart ───────────────────────────────────────────────────── */
function SimpleBarChart({ data, color }: { data: { label: string; value: number }[]; color: string }) {
    const max = Math.max(...data.map(d => d.value), 1);
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {data.map((d, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 80, fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {d.label}
                    </div>
                    <div style={{ flex: 1, height: 8, background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min((d.value / max) * 100, 100)}%`, background: color, borderRadius: 4, transition: 'width 0.5s' }} />
                    </div>
                    <div style={{ width: 50, fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace", textAlign: 'right', flexShrink: 0 }}>
                        {d.value.toLocaleString()}
                    </div>
                </div>
            ))}
        </div>
    );
}

/* ── Severity Badge ─────────────────────────────────────────────────────── */
function getSeverityBadge(cellLoad: number) {
    if (cellLoad > 85) return { cls: 'badge-danger', label: 'CRITICAL' };
    if (cellLoad > 60) return { cls: 'badge-warning', label: 'WARNING' };
    return { cls: 'badge-info', label: 'ELEVATED' };
}

/* ── Main ────────────────────────────────────────────────────────────────── */
export default function VAEAnomaliesPage() {
    const [data, setData] = useState<VAEData | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        try {
            const res = await fetch('/api/vae-anomalies', { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to fetch');
            const json = await res.json();
            setData(json);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    if (loading) {
        return (
            <div className="l4-loading">
                <div className="l4-loading-spinner" />
                <div className="l4-loading-text">Loading VAE Anomalies...</div>
            </div>
        );
    }

    if (!data) {
        return <div className="empty-state"><div className="empty-state-text">Failed to load VAE anomaly data</div></div>;
    }

    const { summary, byArea, byCell, recentAnomalies, reconstructionError, threshold } = data;

    const areaChartData = byArea.slice(0, 10).map(a => ({
        label: a.area,
        value: a.anomaly_count,
    }));

    const cellChartData = byCell.slice(0, 10).map(c => ({
        label: c.cell_id,
        value: c.anomaly_count,
    }));

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Detection · PyTorch VAE v3.0-gpu"
                description="Variational Autoencoder anomaly detection on OSS cell KPIs. 9 features → 32 → 16 → Latent(8) → 16 → 32 → 9. Trained on 500K records. Threshold optimized for 70% recall. ROC-AUC = 0.931."
                values={[
                    { text: `${summary.total.toLocaleString()} OSS records analyzed` },
                    { text: `${summary.anomaly_count.toLocaleString()} anomalies detected (${summary.anomaly_rate}%)` },
                    { text: `Threshold: ${threshold} · Avg anomalous cell load: ${summary.avg_cell_load_anomalous}%` },
                ]}
            />

            {/* KPI Cards */}
            <div className="grid grid-4">
                <div className="card card-compact">
                    <div className="stat-label">Total Records</div>
                    <div className="stat-value">{summary.total.toLocaleString()}</div>
                </div>
                <div className="card card-compact">
                    <div className="stat-label">Anomaly Count</div>
                    <div className="stat-value" style={{ color: 'var(--color-danger)' }}>{summary.anomaly_count.toLocaleString()}</div>
                </div>
                <div className="card card-compact">
                    <div className="stat-label">Anomaly Rate</div>
                    <div className="stat-value" style={{ color: 'var(--color-warning)' }}>{summary.anomaly_rate}%</div>
                </div>
                <div className="card card-compact">
                    <div className="stat-label">Avg Cell Load (Anomalous)</div>
                    <div className="stat-value" style={{ color: 'var(--color-info)' }}>{summary.avg_cell_load_anomalous}%</div>
                </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-2">
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot" />
                        Reconstruction Error Distribution
                        <span className="section-subtitle">Normal vs anomalous · threshold {threshold}</span>
                    </div>
                    <StackedBarChart data={reconstructionError} />
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 12 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--color-success)' }} />
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Normal</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--color-danger)' }} />
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Anomalous</span>
                        </div>
                    </div>
                </div>
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot" />
                        Anomalies by Area
                        <span className="section-subtitle">Top 10 areas by count</span>
                    </div>
                    <SimpleBarChart data={areaChartData} color="#ef4444" />
                </div>
            </div>

            {/* Cell Distribution + Recent Anomalies */}
            <div className="grid grid-2">
                <div className="card">
                    <div className="section-title">
                        <span className="dot" />
                        Top Anomalous Cells
                        <span className="section-subtitle">By anomaly count</span>
                    </div>
                    <SimpleBarChart data={cellChartData} color="#f97316" />
                </div>
                <div className="card">
                    <div className="section-title">
                        <span className="dot" />
                        Recent Anomalies
                        <span className="section-subtitle">Last 50 anomalous records</span>
                    </div>
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Cell ID</th>
                                    <th>Area</th>
                                    <th>Throughput</th>
                                    <th>Latency</th>
                                    <th>Packet Loss</th>
                                    <th>Cell Load</th>
                                    <th>Severity</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentAnomalies.map((a, i) => {
                                    const badge = getSeverityBadge(a.cell_load_pct ?? 0);
                                    return (
                                        <tr key={i}>
                                            <td className="mono">{a.cell_id}</td>
                                            <td>{a.area}</td>
                                            <td className="mono">{a.throughput_mbps?.toFixed(1) ?? '—'} Mbps</td>
                                            <td className="mono">{a.latency_ms?.toFixed(1) ?? '—'} ms</td>
                                            <td className="mono">{(a.packet_loss_rate * 100)?.toFixed(2) ?? '—'}%</td>
                                            <td className="mono">{a.cell_load_pct?.toFixed(1) ?? '—'}%</td>
                                            <td><span className={`badge ${badge.cls}`}>{badge.label}</span></td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
