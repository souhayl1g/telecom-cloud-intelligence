"use client";
import { useEffect, useMemo, useState, useCallback } from 'react';
import PageInfoBar from '../../components/PageInfoBar';
import TunisiaMap from '../../components/TunisiaMap';
import GovernorateDetailPanel from '../../components/GovernorateDetailPanel';
import { aggregateByGovernorate, areaToGovernorate } from '../../lib/tunisia-areas';
import { MapPin, Activity, AlertTriangle, Gauge, ServerCrash } from 'lucide-react';
import { PageSkeleton } from '../../components/ui/LoadingSkeleton';
import ErrorState from '../../components/ui/ErrorState';
import EmptyState from '../../components/ui/EmptyState';
import StatTile from '../../components/ui/StatTile';

/* ── Types ──────────────────────────────────────────────────────────────── */
interface VAEData {
    summary: { total: number; anomaly_count: number; anomaly_rate: number; avg_cell_load_anomalous: number };
    byArea: { area: string; total: number; anomaly_count: number; rate: number }[];
    byCell: { cell_id: string; area: string; total: number; anomaly_count: number; rate: number }[];
    recentAnomalies: { cell_id: string; area: string; throughput_mbps: number; latency_ms: number; packet_loss_rate: number; cell_load_pct: number; timestamp: string }[];
    reconstructionError: { bin: string; normal: number; anomaly: number }[];
    threshold: number;
    byAreaMonthly?: { month_year: string; area: string; total: number; anomaly_count: number; rate: number }[];
    granger?: { area?: string; oss_variable: string; cem_variable: string; direction?: string; best_lag: number; best_pvalue: number; significant?: boolean }[];
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
    const [error, setError] = useState<string | null>(null);
    const [selectedGov, setSelectedGov] = useState<string | null>(null);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/api/vae-anomalies', { cache: 'no-store' });
            if (!res.ok) throw new Error(`HTTP ${res.status} — ${res.statusText}`);
            const json = await res.json();
            setData(json);
        } catch (err: any) {
            console.error(err);
            setError(err?.message ?? 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Hooks MUST run on every render in stable order — keep useMemo above any
    // conditional return, null-guard the data dependency inside the factory.
    const mapFrames = useMemo(() => {
        const monthly = data?.byAreaMonthly ?? [];
        if (monthly.length === 0) return undefined;
        const byMonth = new Map<string, { area: string; total: number; anomaly_count: number; rate: number }[]>();
        for (const r of monthly) {
            const list = byMonth.get(r.month_year) ?? [];
            list.push({ area: r.area, total: r.total, anomaly_count: r.anomaly_count, rate: r.rate });
            byMonth.set(r.month_year, list);
        }
        return Array.from(byMonth.entries())
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([month, rows]) => ({ label: month, rows: aggregateByGovernorate(rows) }));
    }, [data?.byAreaMonthly]);

    if (loading) {
        return <PageSkeleton withChart />;
    }

    if (error || !data) {
        return (
            <ErrorState
                title="Could not load VAE anomalies"
                message={error ?? 'No data returned from /api/vae-anomalies. The pipeline may not have produced results yet.'}
                onRetry={fetchData}
            />
        );
    }

    if (data.summary.total === 0) {
        return (
            <EmptyState
                title="No anomaly data yet"
                description="Run a pipeline cycle to populate the VAE anomaly detector. Results appear here within 2 minutes."
                icon={ServerCrash}
            />
        );
    }

    const { summary, byArea, byCell, recentAnomalies, reconstructionError, threshold } = data;

    // Aggregate cell-level area codes into Tunisia governorates
    const governorateRows = aggregateByGovernorate(byArea);
    const maxGovAnoms = Math.max(...governorateRows.map(r => r.anomaly_count), 1);
    const selectedRow = governorateRows.find(r => r.governorate === selectedGov);

    const cellChartData = byCell.slice(0, 10).map(c => ({
        label: c.cell_id,
        value: c.anomaly_count,
    }));

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Detection · PyTorch VAE v3.0-gpu"
                description="Variational Autoencoder anomaly detection on OSS cell KPIs. 9 features → 32 → 16 → Latent(8) → 16 → 32 → 9. Trained on 500K records. Threshold optimized for 70% recall. ROC-AUC = 0.9821."
                values={[
                    { text: `${summary.total.toLocaleString()} OSS records analyzed` },
                    { text: `${summary.anomaly_count.toLocaleString()} anomalies detected (${summary.anomaly_rate}%)` },
                    { text: `Threshold: ${threshold} · Avg anomalous cell load: ${summary.avg_cell_load_anomalous}%` },
                ]}
            />

            {/* KPI tiles */}
            <div className="grid grid-4">
                <StatTile
                    label="Total Records"
                    value={summary.total.toLocaleString()}
                    icon={Activity}
                    sub="OSS cell measurements analyzed"
                />
                <StatTile
                    label="Anomaly Count"
                    value={summary.anomaly_count.toLocaleString()}
                    icon={AlertTriangle}
                    tone="danger"
                    sub="VAE reconstruction error > threshold"
                />
                <StatTile
                    label="Anomaly Rate"
                    value={`${summary.anomaly_rate}%`}
                    icon={Gauge}
                    tone="warning"
                    sub="of all cell measurements"
                />
                <StatTile
                    label="Avg Cell Load (anom.)"
                    value={`${summary.avg_cell_load_anomalous}%`}
                    icon={Gauge}
                    tone="info"
                    sub="anomalous cells run hotter"
                />
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
                        Anomalies by Governorate
                        <span className="section-subtitle">{governorateRows.length} regions · scroll for all</span>
                    </div>
                    <div className="gov-list-scroll">
                        {governorateRows.map((r) => (
                            <div key={r.governorate} className="gov-row">
                                <div className="gov-row-name">
                                    <MapPin size={13} strokeWidth={2.2} className="gov-row-pin" />
                                    <span>{r.governorate}</span>
                                    <span className="gov-row-cells">{r.cell_count ?? 0} cells</span>
                                </div>
                                <div className="gov-row-bar">
                                    <div
                                        className="gov-row-bar-fill"
                                        style={{ width: `${Math.min((r.anomaly_count / maxGovAnoms) * 100, 100)}%` }}
                                    />
                                </div>
                                <div className="gov-row-value">{(r.anomaly_count ?? 0).toLocaleString()}</div>
                                <div className="gov-row-rate">{r.rate ?? 0}%</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Tunisia Anomaly Map — animated + click-to-explain */}
            <div className="card card-accent-top">
                <div className="section-title">
                    <span className="dot" />
                    Tunisia Anomaly Heat Map
                    <span className="section-subtitle">
                        {mapFrames ? `${mapFrames.length}-frame temporal animation · ` : ''}
                        click governorate for Granger-derived causes · {governorateRows.length} regions
                    </span>
                </div>
                <div className="tunisia-map-container with-panel">
                    <TunisiaMap
                        rows={governorateRows}
                        metric="anomaly_count"
                        frames={mapFrames}
                        selected={selectedGov}
                        onSelect={setSelectedGov}
                    />
                    <GovernorateDetailPanel
                        governorate={selectedGov}
                        row={selectedRow}
                        grangerAll={data.granger ?? []}
                        cellsAll={byCell}
                        recentAll={recentAnomalies}
                        onClose={() => setSelectedGov(null)}
                    />
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
                                    const gov = areaToGovernorate(a.area);
                                    return (
                                        <tr key={`${a.cell_id}-${i}`}>
                                            <td className="mono">{a.cell_id}</td>
                                            <td>{gov ?? a.area}</td>
                                            <td className="mono">{a.throughput_mbps?.toFixed(1) ?? '—'} Mbps</td>
                                            <td className="mono">{a.latency_ms?.toFixed(1) ?? '—'} ms</td>
                                            <td className="mono">{a.packet_loss_rate != null ? (a.packet_loss_rate * 100).toFixed(2) + '%' : '—'}</td>
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
