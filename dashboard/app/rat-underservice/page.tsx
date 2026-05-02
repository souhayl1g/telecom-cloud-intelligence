"use client";
import { useEffect, useState, useCallback } from 'react';
import PageInfoBar from '../../components/PageInfoBar';

/* ── Types ──────────────────────────────────────────────────────────────── */
interface RATData {
    overall: { total: number; underserved: number; rate: number };
    byGeneration: { generation: string; total: number; underserved: number; rate: number }[];
    byArea: { area: string; total: number; underserved: number; rate: number }[];
    topUnderserved: { imsi_hash: string; rat_gap_score: number; area: string; generation: string; highest_rat: string }[];
}

/* ── Donut Chart ─────────────────────────────────────────────────────────── */
function DonutChart({ data, colors }: { data: { label: string; value: number }[]; colors: string[] }) {
    const total = data.reduce((sum, d) => sum + d.value, 0) || 1;
    let accumulated = 0;
    const size = 160;
    const cx = size / 2;
    const cy = size / 2;
    const r = 60;
    const innerR = 40;

    const segments = data.map((d, i) => {
        const startAngle = (accumulated / total) * Math.PI * 2 - Math.PI / 2;
        accumulated += d.value;
        const endAngle = (accumulated / total) * Math.PI * 2 - Math.PI / 2;

        const x1 = cx + r * Math.cos(startAngle);
        const y1 = cy + r * Math.sin(startAngle);
        const x2 = cx + r * Math.cos(endAngle);
        const y2 = cy + r * Math.sin(endAngle);
        const x3 = cx + innerR * Math.cos(endAngle);
        const y3 = cy + innerR * Math.sin(endAngle);
        const x4 = cx + innerR * Math.cos(startAngle);
        const y4 = cy + innerR * Math.sin(startAngle);

        const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;

        return {
            path: `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerR} ${innerR} 0 ${largeArc} 0 ${x4} ${y4} Z`,
            color: colors[i % colors.length],
            label: d.label,
            value: d.value,
        };
    });

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
                {segments.map((s, i) => (
                    <path key={i} d={s.path} fill={s.color} opacity={0.9} />
                ))}
            </svg>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {segments.map((s, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 10, height: 10, borderRadius: 3, background: s.color }} />
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{s.label}</span>
                        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>
                            {s.value.toLocaleString()}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ── Rate Bar Chart ─────────────────────────────────────────────────────── */
function RateBarChart({ data }: { data: { label: string; value: number }[] }) {
    const max = Math.max(...data.map(d => d.value), 1);
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {data.map((d, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 100, fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {d.label}
                    </div>
                    <div style={{ flex: 1, height: 10, background: 'var(--bg-elevated)', borderRadius: 5, overflow: 'hidden' }}>
                        <div style={{
                            height: '100%',
                            width: `${Math.min((d.value / max) * 100, 100)}%`,
                            background: d.value > 15 ? 'var(--color-danger)' : d.value > 8 ? 'var(--color-warning)' : 'var(--color-success)',
                            borderRadius: 5,
                            transition: 'width 0.5s'
                        }} />
                    </div>
                    <div style={{ width: 50, fontSize: 12, fontWeight: 700, color: d.value > 15 ? 'var(--color-danger)' : d.value > 8 ? 'var(--color-warning)' : 'var(--color-success)', fontFamily: "'JetBrains Mono', monospace", textAlign: 'right', flexShrink: 0 }}>
                        {d.value.toFixed(1)}%
                    </div>
                </div>
            ))}
        </div>
    );
}

/* ── Main ────────────────────────────────────────────────────────────────── */
export default function RATUnderservicePage() {
    const [data, setData] = useState<RATData | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        try {
            const res = await fetch('/api/rat-underservice', { cache: 'no-store' });
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
                <div className="l4-loading-text">Loading RAT Underservice...</div>
            </div>
        );
    }

    if (!data) {
        return <div className="empty-state"><div className="empty-state-text">Failed to load RAT data</div></div>;
    }

    const { overall, byGeneration, byArea, topUnderserved } = data;

    const gen4G = byGeneration.find(g => g.generation === '4G');
    const gen5G = byGeneration.find(g => g.generation === '5G');
    const gen4GRate = gen4G?.rate ?? 0;
    const gen5GRate = gen5G?.rate ?? 0;

    const donutData = byGeneration.map(g => ({
        label: g.generation,
        value: g.underserved,
    }));

    const areaData = byArea.slice(0, 12).map(a => ({
        label: a.area,
        value: a.rate,
    }));

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Detection · XGBoost v3.0-gpu"
                description="RAT (Radio Access Technology) underservice detection identifies subscribers whose device generation (4G/5G) exceeds the network RAT they are actually served on. XGBoost classifier trained on 2.47M subscribers. F1 = 0.560, Recall = 0.893."
                values={[
                    { text: `${overall.total.toLocaleString()} subscribers analyzed` },
                    { text: `${overall.underserved.toLocaleString()} underserved (${overall.rate}%)` },
                    { text: `4G underserved: ${gen4GRate}% · 5G underserved: ${gen5GRate}%` },
                ]}
            />

            {/* KPI Cards */}
            <div className="grid grid-4">
                <div className="card card-compact">
                    <div className="stat-label">Total Analyzed</div>
                    <div className="stat-value">{overall.total.toLocaleString()}</div>
                </div>
                <div className="card card-compact">
                    <div className="stat-label">Underserved Rate</div>
                    <div className="stat-value" style={{ color: overall.rate > 10 ? 'var(--color-danger)' : 'var(--color-warning)' }}>
                        {overall.rate}%
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-label">4G Underserved</div>
                    <div className="stat-value" style={{ color: gen4GRate > 10 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                        {gen4GRate}%
                    </div>
                    <div className="stat-sub">{gen4G?.underserved.toLocaleString() ?? 0} subscribers</div>
                </div>
                <div className="card card-compact">
                    <div className="stat-label">5G Underserved</div>
                    <div className="stat-value" style={{ color: gen5GRate > 10 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                        {gen5GRate}%
                    </div>
                    <div className="stat-sub">{gen5G?.underserved.toLocaleString() ?? 0} subscribers</div>
                </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-2">
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot" />
                        Underserved by Generation
                        <span className="section-subtitle">Absolute count distribution</span>
                    </div>
                    <DonutChart
                        data={donutData}
                        colors={['#60a5fa', '#f472b6', '#fbbf24', '#34d399']}
                    />
                </div>
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot" />
                        Underserved Rate by Area
                        <span className="section-subtitle">Top 12 areas by percentage</span>
                    </div>
                    <RateBarChart data={areaData} />
                </div>
            </div>

            {/* Table */}
            <div className="card">
                <div className="section-title">
                    <span className="dot" />
                    Most Underserved Subscribers
                    <span className="section-subtitle">Top 50 by RAT gap score</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>IMSI Hash</th>
                                <th>RAT Gap Score</th>
                                <th>Area</th>
                                <th>Generation</th>
                                <th>Highest RAT</th>
                                <th>Risk</th>
                            </tr>
                        </thead>
                        <tbody>
                            {topUnderserved.map((s, i) => (
                                <tr key={i}>
                                    <td className="mono">{s.imsi_hash.slice(0, 16)}...</td>
                                    <td style={{ fontWeight: 700, color: s.rat_gap_score > 0.5 ? 'var(--color-danger)' : 'var(--color-warning)' }}>
                                        {s.rat_gap_score.toFixed(4)}
                                    </td>
                                    <td>{s.area || '—'}</td>
                                    <td>{s.generation || '—'}</td>
                                    <td>{s.highest_rat || '—'}</td>
                                    <td>
                                        {s.rat_gap_score > 0.5 ? (
                                            <span className="badge badge-danger">HIGH</span>
                                        ) : (
                                            <span className="badge badge-warning">MEDIUM</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
