"use client";
import { useEffect, useState, useCallback } from 'react';
import PageInfoBar from '../../components/PageInfoBar';
import { Users, Smile, Frown, Meh, BarChart3 } from 'lucide-react';
import { PageSkeleton } from '../../components/ui/LoadingSkeleton';
import ErrorState from '../../components/ui/ErrorState';
import EmptyState from '../../components/ui/EmptyState';
import StatTile from '../../components/ui/StatTile';
import { areaToGovernorate } from '../../lib/tunisia-areas';
import { safeFixed } from '../../lib/time';

/* ── Types ──────────────────────────────────────────────────────────────── */
interface CEMData {
    distribution: { bucket: number; count: number; min_score: number; max_score: number }[];
    areaAverages: { area: string; avg_cem_score: number; subscriber_count: number }[];
    topHighest: { imsi_hash: string; cem_score: number; area: string; generation: string }[];
    topLowest: { imsi_hash: string; cem_score: number; area: string; generation: string }[];
    summary: { total: number; avg_score: number; poor_count: number; fair_count: number; good_count: number };
}

type FilterRange = 'all' | 'poor' | 'fair' | 'good';

/* ── SVG Histogram ───────────────────────────────────────────────────────── */
function Histogram({ data, color }: { data: { label: string; count: number }[]; color: string }) {
    const maxCount = Math.max(...data.map(d => d.count), 1);
    const height = 180;
    const barWidth = 28;
    const gap = 2;
    const totalWidth = data.length * (barWidth + gap);

    return (
        <svg width="100%" height={height} viewBox={`0 0 ${totalWidth} ${height}`} preserveAspectRatio="xMidYMid meet">
            {data.map((d, i) => {
                const barHeight = (d.count / maxCount) * (height - 28);
                const x = i * (barWidth + gap);
                return (
                    <g key={i}>
                        <rect
                            x={x}
                            y={height - 22 - barHeight}
                            width={barWidth}
                            height={barHeight}
                            fill={color}
                            opacity={0.85}
                            rx={3}
                        />
                        <text
                            x={x + barWidth / 2}
                            y={height - 6}
                            textAnchor="middle"
                            style={{ fontSize: 8, fill: 'var(--text-muted)' }}
                        >
                            {d.label}
                        </text>
                    </g>
                );
            })}
        </svg>
    );
}

/* ── Horizontal Bar Chart ───────────────────────────────────────────────── */
function HorizontalBarChart({ data, color, maxValue }: { data: { label: string; value: number }[]; color: string; maxValue?: number }) {
    const max = maxValue || Math.max(...data.map(d => d.value), 1);
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
                    <div style={{ width: 56, fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace", textAlign: 'right', flexShrink: 0 }}>
                        {safeFixed(d.value, 3)}
                    </div>
                </div>
            ))}
        </div>
    );
}

/* ── Score Badge ─────────────────────────────────────────────────────────── */
function ScoreBadge({ score }: { score: number }) {
    if (score >= 0.6) return <span className="badge badge-success">GOOD</span>;
    if (score >= 0.3) return <span className="badge badge-warning">FAIR</span>;
    return <span className="badge badge-danger">POOR</span>;
}

/* ── Main ────────────────────────────────────────────────────────────────── */
export default function CEMScoresPage() {
    const [data, setData] = useState<CEMData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<FilterRange>('all');

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/api/cem-scores', { cache: 'no-store' });
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

    if (loading) {
        return <PageSkeleton withChart />;
    }

    if (error || !data) {
        return (
            <ErrorState
                title="Could not load CEM scores"
                message={error ?? 'No data returned from /api/cem-scores.'}
                onRetry={fetchData}
            />
        );
    }

    if (!data.summary?.total) {
        return (
            <EmptyState
                title="No CEM scores yet"
                description="The CEM scoring model needs a completed pipeline run to populate this page."
                icon={Meh}
            />
        );
    }

    const { summary, distribution, areaAverages, topHighest, topLowest } = data;

    const filterSubscribers = (subscribers: typeof topHighest) => {
        if (filter === 'all') return subscribers;
        return subscribers.filter(s => {
            if (filter === 'poor') return s.cem_score < 0.3;
            if (filter === 'fair') return s.cem_score >= 0.3 && s.cem_score < 0.6;
            return s.cem_score >= 0.6;
        });
    };

    const filteredHighest = filter === 'all' ? topHighest : filterSubscribers(topHighest);
    const filteredLowest = filter === 'all' ? topLowest : filterSubscribers(topLowest);

    const histData = distribution
        .filter(d => d.bucket > 0 && d.bucket <= 20)
        .map(d => ({
            label: `${((d.bucket - 1) * 5)}`,
            count: Number(d.count),
        }));

    // Aggregate CEM scores by Tunisia governorate (weighted by subscriber count)
    const govBuckets = new Map<string, { totalScore: number; subs: number }>();
    for (const a of areaAverages) {
        const gov = areaToGovernorate(a.area) ?? 'Other';
        const b = govBuckets.get(gov) ?? { totalScore: 0, subs: 0 };
        b.totalScore += a.avg_cem_score * a.subscriber_count;
        b.subs += a.subscriber_count;
        govBuckets.set(gov, b);
    }
    const areaChartData = Array.from(govBuckets.entries())
        .map(([gov, b]) => ({ label: gov, value: b.subs > 0 ? b.totalScore / b.subs : 0 }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 24);

    const poorPct = summary.total > 0 ? (summary.poor_count / summary.total) * 100 : 0;
    const fairPct = summary.total > 0 ? (summary.fair_count / summary.total) * 100 : 0;
    const goodPct = summary.total > 0 ? (summary.good_count / summary.total) * 100 : 0;

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Experience · LightGBM DART v3.0"
                description="Customer Experience Management (CEM) scores derived from 13 features across 2.47M Tunisie Telecom subscribers. Scores range 0–1: poor (<0.3), fair (0.3–0.6), good (>0.6). Model R² = 0.9933 on test set."
                values={[
                    { text: `${summary.total.toLocaleString()} subscribers scored` },
                    { text: `Average CEM: ${safeFixed(summary.avg_score, 3)}` },
                    { text: `${goodPct.toFixed(1)}% good experience` },
                ]}
            />

            {/* KPI tiles */}
            <div className="grid grid-4">
                <StatTile
                    label="Total Subscribers"
                    value={summary.total.toLocaleString()}
                    icon={Users}
                    sub="scored via LightGBM CEM v3.0"
                />
                <StatTile
                    label="Average CEM Score"
                    value={safeFixed(summary.avg_score, 3)}
                    icon={BarChart3}
                    tone="info"
                    sub="0.0 worst · 1.0 best"
                />
                <StatTile
                    label="Poor Experience"
                    value={`${poorPct.toFixed(1)}%`}
                    icon={Frown}
                    tone="danger"
                    sub={`${summary.poor_count.toLocaleString()} subscribers`}
                />
                <StatTile
                    label="Good Experience"
                    value={`${goodPct.toFixed(1)}%`}
                    icon={Smile}
                    tone="success"
                    sub={`${summary.good_count.toLocaleString()} subscribers`}
                />
            </div>

            {/* Filters */}
            <div className="card card-compact" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {([
                    { key: 'all' as FilterRange, label: 'All Scores', color: 'var(--text-secondary)' },
                    { key: 'poor' as FilterRange, label: 'Poor (0–0.3)', color: 'var(--color-danger)' },
                    { key: 'fair' as FilterRange, label: 'Fair (0.3–0.6)', color: 'var(--color-warning)' },
                    { key: 'good' as FilterRange, label: 'Good (0.6–1.0)', color: 'var(--color-success)' },
                ]).map(f => (
                    <button
                        key={f.key}
                        onClick={() => setFilter(f.key)}
                        className={`dash-time-btn ${filter === f.key ? 'dash-time-active' : ''}`}
                        style={filter === f.key ? { background: f.color, borderColor: f.color, color: '#fff' } : {}}
                    >
                        {f.label}
                    </button>
                ))}
            </div>

            {/* Charts Row */}
            <div className="grid grid-2">
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot" />
                        CEM Score Distribution
                        <span className="section-subtitle">20 buckets across 0–1.0 range</span>
                    </div>
                    <Histogram data={histData} color="#a78bfa" />
                </div>
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot" />
                        Average CEM by Area
                        <span className="section-subtitle">Top 12 areas by score</span>
                    </div>
                    <HorizontalBarChart data={areaChartData} color="#34d399" maxValue={1} />
                </div>
            </div>

            {/* Tables Row */}
            <div className="grid grid-2">
                <div className="card">
                    <div className="section-title">
                        <span className="dot" />
                        Top 10 Highest CEM
                        <span className="section-subtitle">Best subscriber experience</span>
                    </div>
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>IMSI Hash</th>
                                    <th>Score</th>
                                    <th>Area</th>
                                    <th>Generation</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredHighest.map((s, i) => (
                                    <tr key={i}>
                                        <td className="mono">{s.imsi_hash.slice(0, 16)}...</td>
                                        <td style={{ fontWeight: 700, color: 'var(--color-success)' }}>{safeFixed(s.cem_score, 4)}</td>
                                        <td>{areaToGovernorate(s.area) ?? s.area ?? '—'}</td>
                                        <td>{s.generation || '—'}</td>
                                        <td><ScoreBadge score={s.cem_score} /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div className="card">
                    <div className="section-title">
                        <span className="dot" />
                        Top 10 Lowest CEM
                        <span className="section-subtitle">At-risk subscriber experience</span>
                    </div>
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>IMSI Hash</th>
                                    <th>Score</th>
                                    <th>Area</th>
                                    <th>Generation</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredLowest.map((s, i) => (
                                    <tr key={i}>
                                        <td className="mono">{s.imsi_hash.slice(0, 16)}...</td>
                                        <td style={{ fontWeight: 700, color: 'var(--color-danger)' }}>{safeFixed(s.cem_score, 4)}</td>
                                        <td>{areaToGovernorate(s.area) ?? s.area ?? '—'}</td>
                                        <td>{s.generation || '—'}</td>
                                        <td><ScoreBadge score={s.cem_score} /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
