"use client";

import { useCallback, useEffect, useMemo, useState } from 'react';
import PageInfoBar from '../../components/PageInfoBar';
import StatTile from '../../components/ui/StatTile';
import { PageSkeleton } from '../../components/ui/LoadingSkeleton';
import ErrorState from '../../components/ui/ErrorState';
import EmptyState from '../../components/ui/EmptyState';
import {
    ArrowRight, Clock, Sigma, Activity, AlertTriangle, GitBranch, Layers,
    TrendingDown, TrendingUp, MapPin, Info, FlaskConical,
} from 'lucide-react';

/* ── Types ──────────────────────────────────────────────────────────────── */
interface Projection {
    area: string;
    oss_variable: string;
    cem_variable: string;
    best_lag: number;
    lead_time_minutes: number;
    p_value: number;
    direction?: string;
    n_observations: number;
    fit_intercept: number;
    fit_slope: number;
    fit_r2: number;
    latest_oss: number | null;
    current_cem: number | null;
    projected_cem: number;
    delta_cem: number | null;
}

interface ForecastResp {
    lag_window_minutes: number;
    area_filter: string | null;
    projections: Projection[];
    note?: string;
}

/* ── Helpers ────────────────────────────────────────────────────────────── */
function pValueBadge(p: number): { label: string; cls: string } {
    if (p < 0.01) return { label: 'p<0.01', cls: 'badge-danger' };
    if (p < 0.05) return { label: 'p<0.05', cls: 'badge-warning' };
    if (p < 0.10) return { label: 'p<0.10', cls: 'badge-info' };
    return { label: `p=${p.toFixed(3)}`, cls: 'badge-muted' };
}

function r2Tone(r2: number): 'success' | 'info' | 'warning' | 'danger' {
    if (r2 >= 0.6) return 'success';
    if (r2 >= 0.3) return 'info';
    if (r2 >= 0.1) return 'warning';
    return 'danger';
}

function fmtLead(min: number): string {
    if (min < 60) return `${Math.round(min)} min`;
    const h = min / 60;
    if (h < 48) return `${h.toFixed(1)} h`;
    return `${(h / 24).toFixed(1)} d`;
}

/** Tiny inline forecast sparkline: shows current and projected CEM as two points
 *  separated by an arrow on a normalized 0..1 axis. No mock historical extrapolation. */
function CausalSparkline({ current, projected, color }: { current: number | null; projected: number; color: string }) {
    const w = 220;
    const h = 56;
    const y = (v: number) => h - 8 - Math.max(0, Math.min(1, v)) * (h - 16);
    const c = current ?? projected;
    return (
        <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block' }}>
            <line x1={0} y1={h - 8} x2={w} y2={h - 8} stroke="rgba(15,23,42,0.08)" strokeWidth={1} />
            <line x1={w / 2} y1={0} x2={w / 2} y2={h} stroke="rgba(15,23,42,0.06)" strokeWidth={1} strokeDasharray="3,3" />
            <text x={4} y={11} fontSize={9} fill="#94A3B8" fontFamily="'Fira Code', monospace">now</text>
            <text x={w - 4} y={11} fontSize={9} fill="#94A3B8" fontFamily="'Fira Code', monospace" textAnchor="end">+lag</text>
            <line x1={20} y1={y(c)} x2={w - 20} y2={y(projected)} stroke={color} strokeWidth={2} strokeLinecap="round" />
            <circle cx={20} cy={y(c)} r={4} fill={color} />
            <circle cx={w - 20} cy={y(projected)} r={4} fill={color} stroke="#FFFFFF" strokeWidth={1.5} />
            <text x={20} y={y(c) - 8} fontSize={10} fill="#0F172A" textAnchor="start" fontWeight={700} fontFamily="var(--font-geist), sans-serif">
                {c.toFixed(3)}
            </text>
            <text x={w - 20} y={y(projected) - 8} fontSize={10} fill={color} textAnchor="end" fontWeight={700} fontFamily="var(--font-geist), sans-serif">
                {projected.toFixed(3)}
            </text>
        </svg>
    );
}

/* ── Page ───────────────────────────────────────────────────────────────── */
export default function PredictivePage() {
    const [resp, setResp] = useState<ForecastResp | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [area, setArea] = useState<string>(''); // empty = all areas

    const fetchForecast = useCallback(async (a: string) => {
        setLoading(true);
        setError(null);
        try {
            const url = `/api/granger-forecast${a ? `?area=${encodeURIComponent(a)}` : ''}`;
            const r = await fetch(url, { cache: 'no-store' });
            if (!r.ok) throw new Error(`HTTP ${r.status} ${r.statusText}`);
            setResp(await r.json());
        } catch (err: any) {
            setError(err?.message ?? 'Forecast fetch failed');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchForecast(area); }, [area, fetchForecast]);

    // List of areas inferred from projections — populates the dropdown.
    const allAreas = useMemo(() => {
        const set = new Set<string>();
        (resp?.projections ?? []).forEach((p) => set.add(p.area));
        return Array.from(set).sort();
    }, [resp]);

    if (loading) return <PageSkeleton withChart />;
    if (error) return <ErrorState title="Could not load Granger forecast" message={error} onRetry={() => fetchForecast(area)} />;
    if (!resp) return null;

    const projections = resp.projections;
    const lagWin = resp.lag_window_minutes;

    if (projections.length === 0) {
        return (
            <div className="grid" style={{ gap: 24 }}>
                <PageInfoBar
                    eyebrow="Forecast · Granger causal projection"
                    description="CEM-side projections computed from significant OSS→CEM Granger pairs. Each projection fits a local OLS regression on the area's monthly panel from area_network_health and projects the CEM variable forward by best_lag cycles."
                    values={[
                        { text: `Lag window: ${lagWin.toLocaleString()} min per Granger lag` },
                        { text: 'No projections available yet' },
                    ]}
                />
                <EmptyState
                    title="No Granger-significant pairs persisted yet"
                    description={resp.note ?? 'Run the pipeline-worker live engine for at least 3 cycles, then refresh.'}
                    icon={FlaskConical}
                />
            </div>
        );
    }

    // Summary tiles
    const peakDrop = projections.reduce<Projection | null>((acc, p) => {
        if (p.delta_cem == null) return acc;
        if (!acc || p.delta_cem < (acc.delta_cem ?? 0)) return p;
        return acc;
    }, null);
    const peakRise = projections.reduce<Projection | null>((acc, p) => {
        if (p.delta_cem == null) return acc;
        if (!acc || p.delta_cem > (acc.delta_cem ?? 0)) return p;
        return acc;
    }, null);
    const meanR2 = projections.reduce((s, p) => s + p.fit_r2, 0) / projections.length;
    const shortestLead = projections.reduce<Projection>((acc, p) => (p.lead_time_minutes < acc.lead_time_minutes ? p : acc), projections[0]);

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Forecast · Granger causal projection"
                description="CEM-side projections derived from Granger-significant (OSS → CEM) pairs. For each pair we fit OLS  CEM_Y(t) ~ OSS_X(t-best_lag)  on the area's monthly panel from area_network_health, then project CEM_Y at t+best_lag. No mock data; no extrapolation of CEM history alone."
                values={[
                    { text: `${projections.length} causal projections` },
                    { text: `Lag window: ${lagWin.toLocaleString()} min per Granger lag` },
                    { text: `Mean fit R²: ${meanR2.toFixed(3)}` },
                ]}
            />

            {/* Area selector */}
            <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 14 }}>
                <Layers size={14} strokeWidth={2.4} color="#64748B" />
                <label htmlFor="area-select" style={{ fontSize: 12, color: '#475569', fontWeight: 600 }}>Area filter</label>
                <select
                    id="area-select"
                    value={area}
                    onChange={(e) => setArea(e.target.value)}
                    style={{
                        padding: '6px 10px',
                        borderRadius: 8,
                        border: '1px solid var(--border)',
                        fontFamily: "'Fira Code', monospace",
                        fontSize: 12,
                    }}
                >
                    <option value="">All areas</option>
                    {allAreas.map((a) => (
                        <option key={a} value={a}>{a}</option>
                    ))}
                </select>
                <span style={{ fontSize: 11, color: '#94A3B8', marginLeft: 'auto' }}>
                    <Info size={11} strokeWidth={2.4} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                    Each projection is an OLS local fit on N ≥ 3 lagged observations.
                </span>
            </div>

            {/* Headline KPIs */}
            <div className="grid grid-4">
                <StatTile
                    label="Sharpest CEM drop"
                    value={peakDrop?.delta_cem != null ? peakDrop.delta_cem.toFixed(3) : '—'}
                    icon={TrendingDown}
                    tone="danger"
                    sub={peakDrop ? `${peakDrop.area} · ${peakDrop.oss_variable}→${peakDrop.cem_variable}` : 'no decline projected'}
                />
                <StatTile
                    label="Sharpest CEM rise"
                    value={peakRise?.delta_cem != null ? `+${peakRise.delta_cem.toFixed(3)}` : '—'}
                    icon={TrendingUp}
                    tone="success"
                    sub={peakRise ? `${peakRise.area} · ${peakRise.oss_variable}→${peakRise.cem_variable}` : 'no rise projected'}
                />
                <StatTile
                    label="Shortest lead-time"
                    value={fmtLead(shortestLead.lead_time_minutes)}
                    icon={Clock}
                    tone="warning"
                    sub={`${shortestLead.area} · lag=${shortestLead.best_lag}`}
                />
                <StatTile
                    label="Mean fit R²"
                    value={meanR2.toFixed(3)}
                    icon={Sigma}
                    tone={r2Tone(meanR2)}
                    sub={`Across ${projections.length} pairs`}
                />
            </div>

            {/* Projections list */}
            <div className="card">
                <div className="section-title">
                    <span className="dot" />
                    Per-pair causal projections
                    <span className="section-subtitle">Sorted by p-value (most significant first)</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
                    {projections.slice(0, 24).map((p, i) => {
                        const pBadge = pValueBadge(p.p_value);
                        const isDrop = (p.delta_cem ?? 0) < 0;
                        const color = isDrop ? '#DC2626' : '#10B981';
                        const projColor = isDrop ? '#B91C1C' : '#059669';
                        return (
                            <div key={i} className="gov-detail-pair" style={{ padding: 14 }}>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 240px', gap: 18, alignItems: 'center' }}>
                                    <div>
                                        <div className="gov-detail-pair-formula" style={{ marginBottom: 6 }}>
                                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: '#475569', fontSize: 11, marginRight: 6 }}>
                                                <MapPin size={11} strokeWidth={2.4} />
                                                <code style={{ background: 'rgba(15,23,42,0.06)', color: '#0F172A', padding: '2px 6px', borderRadius: 5, fontFamily: "'Fira Code', monospace", fontSize: 11 }}>{p.area}</code>
                                            </span>
                                            <code className="gov-detail-pair-oss">{p.oss_variable}</code>
                                            <ArrowRight size={11} strokeWidth={2.4} />
                                            <code className="gov-detail-pair-cem">{p.cem_variable}</code>
                                            <span className={`badge ${pBadge.cls}`}>{pBadge.label}</span>
                                            <span className="badge badge-info">R²={p.fit_r2.toFixed(2)}</span>
                                            <span className="badge badge-muted">n={p.n_observations}</span>
                                        </div>
                                        <div className="gov-detail-pair-meta">
                                            <span><Clock size={10} strokeWidth={2.4} /> lag={p.best_lag} (~{fmtLead(p.lead_time_minutes)})</span>
                                            <span><Sigma size={10} strokeWidth={2.4} /> β={p.fit_slope.toExponential(2)}</span>
                                            {p.latest_oss != null && (
                                                <span><Activity size={10} strokeWidth={2.4} /> latest {p.oss_variable}={p.latest_oss.toFixed(2)}</span>
                                            )}
                                        </div>
                                        <div className="gov-detail-pair-cause">
                                            <strong>Projection.</strong>{' '}
                                            Current {p.cem_variable}{p.current_cem != null ? ` = ${p.current_cem.toFixed(3)}` : ''} →
                                            projected {p.projected_cem.toFixed(3)} at t+{fmtLead(p.lead_time_minutes)}.
                                            {' '}{isDrop ? 'Predicted decline' : 'Predicted recovery'}: Δ = {p.delta_cem?.toFixed(3) ?? '—'}.
                                        </div>
                                    </div>
                                    <CausalSparkline current={p.current_cem} projected={p.projected_cem} color={color} />
                                </div>
                            </div>
                        );
                    })}
                </div>

                {projections.length > 24 && (
                    <div style={{ marginTop: 10, fontSize: 11, color: '#94A3B8', textAlign: 'center' }}>
                        Showing 24 of {projections.length} projections. Use the area filter to narrow scope.
                    </div>
                )}
            </div>

            {/* Methodology card */}
            <div className="card">
                <div className="section-title">
                    <span className="dot" />
                    Methodology · why this is causal, not extrapolation
                    <span className="section-subtitle">From /granger-causality/explain</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '6px 2px 2px', fontSize: 12, color: '#475569', lineHeight: 1.55 }}>
                    <p>
                        <GitBranch size={12} strokeWidth={2.4} style={{ verticalAlign: 'middle', marginRight: 6, color: '#94A3B8' }} />
                        Each row is a Granger-significant pair: past OSS values <em>statistically predict</em> the CEM
                        variable at lag <code>best_lag</code>. We then fit local OLS
                        <code> CEM_Y(t) ~ a + b · OSS_X(t−lag) </code>
                        on the area's monthly panel and project forward.
                    </p>
                    <p>
                        <AlertTriangle size={12} strokeWidth={2.4} style={{ verticalAlign: 'middle', marginRight: 6, color: '#F59E0B' }} />
                        Naive history-only forecasting (extrapolating CEM forward from itself) does not surface the
                        upstream OSS driver. The Granger-based projection answers the actionable question:
                        <strong> if I fix this OSS variable today, what CEM change should I expect after the lag elapses?</strong>
                    </p>
                </div>
            </div>
        </div>
    );
}
