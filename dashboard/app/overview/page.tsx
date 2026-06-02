import Link from 'next/link';
import { api } from '../../lib/api';
import AnomaliesBarChart from '../../components/AnomaliesBarChart';
import { StaggerGrid, StaggerItem, FadeIn, SlideInBanner } from '../../components/OverviewAnimations';
import PageInfoBar from '../../components/PageInfoBar';
import { formatTunisDateTime } from '../../lib/time';

export const dynamic = 'force-dynamic';

export default async function OverviewPage() {
    // Defensive parallel fetch — one failure doesn't blank the whole dashboard
    const results = await Promise.allSettled([
        api.anomalies(),
        api.cemAnomalies(),
        api.pipelineRuns(),
        api.correlation(),
        api.vaeAnomalies(),
        api.cemScores(),
        api.ratUnderservice(),
    ]);
    const [anomalies, revenue, runs, correlations, vaeSummary, cemSummary, ratSummary] =
        results.map((r) => (r.status === 'fulfilled' ? r.value : null)) as any[];

    const ossCount = anomalies?.length ?? 0;
    const bssCount = revenue?.length ?? 0;
    const totalAnomalies = ossCount + bssCount;
    const successRuns = (runs as any[])?.filter(r => r.status === 'succeeded').length ?? 0;
    const totalRuns = (runs as any[])?.length ?? 0;
    const successRate = totalRuns > 0 ? Math.round((successRuns / totalRuns) * 100) : 0;
    const corrCount = correlations?.length ?? 0;

    const ossCritical = anomalies?.filter((a: any) => a.severity > 0.9).length ?? 0;
    const ossWarning = anomalies?.filter((a: any) => a.severity > 0.5 && a.severity <= 0.9).length ?? 0;
    const strongCorrs = correlations?.filter((c: any) => Math.abs(c.corr_value) >= 0.7).length ?? 0;

    const vaeCount = (vaeSummary as any)?.anomaly_count ?? 0;
    const cemAvg = (cemSummary as any)?.avg_score ?? 0;
    const ratRate = (ratSummary as any)?.rate ?? 0;

    const agentHealth = vaeCount > 50 ? 'critical' : vaeCount > 10 ? 'warning' : 'healthy';
    const pendingActions = (ossCritical > 0 ? 1 : 0) + (vaeCount > 20 ? 1 : 0) + (ratRate > 15 ? 1 : 0);

    return (
        <div className="dash-grid">
            <PageInfoBar
                eyebrow="NeXo Operations · Live"
                description="Real-time view of your network and subscribers. AI watches every cell, scores every customer experience, and flags problems before they spread."
                values={[
                    { text: `${vaeCount.toLocaleString()} active anomalies` },
                    { text: `${pendingActions} action${pendingActions === 1 ? '' : 's'} need attention` },
                    { text: `Health: ${agentHealth.toUpperCase()}` },
                ]}
            />

            {/* ── KPI Cards Row ─────────────────────────── */}
            <StaggerGrid className="dash-kpi-row">
                <StaggerItem>
                    <Link href="/vae-anomalies" className="dash-kpi-card">
                        <div className="dash-kpi-icon dash-kpi-icon-orange">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                            </svg>
                        </div>
                        <div className="dash-kpi-content">
                            <span className="dash-kpi-label">VAE Anomalies</span>
                            <span className="dash-kpi-value">{vaeCount.toLocaleString()}</span>
                            <span className="dash-kpi-sub">PyTorch VAE v3.0-gpu</span>
                        </div>
                        <div className="dash-kpi-mini-bar">
                            <div className="dash-kpi-mini-fill" style={{ width: `${Math.min(100, vaeCount / 5)}%` }} />
                        </div>
                    </Link>
                </StaggerItem>

                <StaggerItem>
                    <Link href="/cem-scores" className="dash-kpi-card">
                        <div className="dash-kpi-icon dash-kpi-icon-green">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
                            </svg>
                        </div>
                        <div className="dash-kpi-content">
                            <span className="dash-kpi-label">Avg CEM Score</span>
                            <span className="dash-kpi-value" style={{
                                color: cemAvg >= 0.6 ? 'var(--color-success)' : cemAvg >= 0.3 ? 'var(--color-warning)' : 'var(--color-danger)'
                            }}>
                                {cemAvg?.toFixed(3) ?? '\u2014'}
                            </span>
                            <span className="dash-kpi-sub">LightGBM DART v3.0</span>
                        </div>
                        <div className="dash-kpi-trend dash-kpi-trend-up">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /></svg>
                        </div>
                    </Link>
                </StaggerItem>

                <StaggerItem>
                    <Link href="/rat-underservice" className="dash-kpi-card">
                        <div className="dash-kpi-icon dash-kpi-icon-blue">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M2 20h20" /><path d="M5 20v-5" /><path d="M9 20v-8" /><path d="M13 20V9" /><path d="M17 20V5" /><path d="M21 20V2" />
                            </svg>
                        </div>
                        <div className="dash-kpi-content">
                            <span className="dash-kpi-label">RAT Underservice</span>
                            <span className="dash-kpi-value" style={{
                                color: ratRate >= 15 ? 'var(--color-danger)' : ratRate >= 8 ? 'var(--color-warning)' : 'var(--color-success)'
                            }}>
                                {ratRate?.toFixed(1) ?? '\u2014'}%
                            </span>
                            <span className="dash-kpi-sub">XGBoost GPU v3.0</span>
                        </div>
                        <div className="dash-kpi-ring">
                            <svg viewBox="0 0 36 36" width="40" height="40">
                                <circle cx="18" cy="18" r="15" fill="none" stroke="var(--border)" strokeWidth="3" />
                                <circle cx="18" cy="18" r="15" fill="none" stroke={ratRate >= 15 ? 'var(--color-danger)' : ratRate >= 8 ? 'var(--color-warning)' : 'var(--color-success)'} strokeWidth="3"
                                    strokeDasharray={`${Math.min(ratRate * 3, 100) * 0.94} 100`}
                                    strokeLinecap="round" transform="rotate(-90 18 18)"
                                    style={{ transition: 'stroke-dasharray 1s ease' }}
                                />
                            </svg>
                        </div>
                    </Link>
                </StaggerItem>

                <StaggerItem>
                    <Link href="/correlations" className="dash-kpi-card">
                        <div className="dash-kpi-icon dash-kpi-icon-blue">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
                                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                            </svg>
                        </div>
                        <div className="dash-kpi-content">
                            <span className="dash-kpi-label">Correlations</span>
                            <span className="dash-kpi-value">{corrCount}</span>
                            <span className="dash-kpi-sub">{strongCorrs} strong | OSS{'\u2194'}CEM</span>
                        </div>
                    </Link>
                </StaggerItem>
            </StaggerGrid>

            {/* ── Main Section: Alert Summary + Recent Data ─── */}
            <FadeIn delay={0.15}>
                <div className="dash-main-row">
                    {/* Left: Alert Summary */}
                    <div className="card dash-alert-card">
                        <div className="section-title" style={{ marginBottom: 12 }}>
                            <span className="dot"></span>
                            Alert Summary
                        </div>
                        <div className="dash-alert-grid">
                            <div className="dash-alert-item dash-alert-critical">
                                <span className="dash-alert-count">{ossCritical}</span>
                                <span className="dash-alert-label">Critical</span>
                                <span className="dash-alert-threshold">&gt;0.9</span>
                            </div>
                            <div className="dash-alert-item dash-alert-warning">
                                <span className="dash-alert-count">{ossWarning}</span>
                                <span className="dash-alert-label">Warning</span>
                                <span className="dash-alert-threshold">0.5-0.9</span>
                            </div>
                            <div className="dash-alert-item dash-alert-low">
                                <span className="dash-alert-count">{ossCount - ossCritical - ossWarning}</span>
                                <span className="dash-alert-label">Low</span>
                                <span className="dash-alert-threshold">&lt;0.5</span>
                            </div>
                        </div>
                    </div>

                    {/* Right: Pipeline Success */}
                    <div className="card">
                        <div className="section-title" style={{ marginBottom: 4 }}>
                            <span className="dot"></span>
                            Pipeline Success
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '12px 0' }}>
                            <svg viewBox="0 0 36 36" width="80" height="80">
                                <circle cx="18" cy="18" r="15" fill="none" stroke="var(--border)" strokeWidth="3" />
                                <circle cx="18" cy="18" r="15" fill="none" stroke="var(--color-success)" strokeWidth="3"
                                    strokeDasharray={`${successRate * 0.94} 100`}
                                    strokeLinecap="round" transform="rotate(-90 18 18)"
                                    style={{ transition: 'stroke-dasharray 1s ease' }}
                                />
                            </svg>
                            <div>
                                <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--color-success)', fontFamily: "'JetBrains Mono', monospace" }}>
                                    {successRate}<span style={{ fontSize: 16 }}>%</span>
                                </div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                    {successRuns}/{totalRuns} runs succeeded
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                                    ~18-step ETL · 30s cycle · 3 v3 models
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </FadeIn>

            {/* ── L4 Agent Banner ──────────────────────── */}
            <SlideInBanner>
                <Link href="/l4-agent" className="dash-agent-banner">
                    <div className="dash-agent-left">
                        <div className="dash-agent-icon-wrap">
                            <div className="dash-agent-pulse-ring" />
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /><circle cx="12" cy="16" r="1" />
                            </svg>
                        </div>
                        <div>
                            <div className="dash-agent-title">
                                L4 Autonomous Agent
                                <span className="dash-agent-model-badge">
                                    <span className="dash-agent-model-dot" />
                                    Qwen2.5 7B
                                </span>
                            </div>
                            <div className="dash-agent-sub">
                                {agentHealth === 'critical'
                                    ? `CRITICAL: ${vaeCount} VAE anomalies, RAT underservice at ${ratRate.toFixed(1)}% \u2014 ${pendingActions} pending actions`
                                    : agentHealth === 'warning'
                                    ? `WARNING: ${vaeCount} VAE anomalies detected \u2014 monitoring ${pendingActions} situation(s)`
                                    : `All systems nominal \u2014 CEM avg ${cemAvg.toFixed(3)}, RAT ${ratRate.toFixed(1)}%, ${vaeCount} VAE anomalies`
                                }
                            </div>
                        </div>
                    </div>
                    <div className="dash-agent-right">
                        <span className={`badge badge-${agentHealth === 'critical' ? 'danger' : agentHealth === 'warning' ? 'warning' : 'success'}`}>
                            {agentHealth.toUpperCase()}
                        </span>
                        <span className="dash-agent-arrow">Open Workspace &rarr;</span>
                    </div>
                </Link>
            </SlideInBanner>

            {/* ── Bottom Row: AI Models Status ─── */}
            <FadeIn delay={0.25}>
                <div className="dash-bottom-row">
                    <div className="card">
                        <div className="section-title">
                            <span className="dot"></span>
                            Anomaly Distribution
                            <span className="section-subtitle">By severity &amp; domain</span>
                        </div>
                        <AnomaliesBarChart ossData={anomalies || []} bssData={revenue || []} />
                    </div>
                    <div className="card">
                        <div className="section-title">
                            <span className="dot"></span>
                            AI Models Status
                            <Link href="/model-evaluation" style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--brand-primary)', fontWeight: 600 }}>View All &rarr;</Link>
                        </div>
                        <div className="dash-models-list">
                            <div className="dash-model-item">
                                <div className="dash-model-dot" style={{ background: '#34d399' }} />
                                <div className="dash-model-info">
                                    <span className="dash-model-name">CEM Experience Score</span>
                                    <span className="dash-model-desc">LightGBM DART &middot; 13 features &middot; 2.47M samples</span>
                                </div>
                                <span className="badge badge-success">v3.0</span>
                            </div>
                            <div className="dash-model-item">
                                <div className="dash-model-dot" style={{ background: '#60a5fa' }} />
                                <div className="dash-model-info">
                                    <span className="dash-model-name">OSS VAE Anomaly</span>
                                    <span className="dash-model-desc">PyTorch VAE &middot; 9 features &middot; 500K samples</span>
                                </div>
                                <span className="badge badge-info">v3.0</span>
                            </div>
                            <div className="dash-model-item">
                                <div className="dash-model-dot" style={{ background: '#fbbf24' }} />
                                <div className="dash-model-info">
                                    <span className="dash-model-name">RAT Underservice</span>
                                    <span className="dash-model-desc">XGBoost GPU &middot; 10 features &middot; 2.47M samples</span>
                                </div>
                                <span className="badge badge-warning">v3.0</span>
                            </div>
                        </div>
                    </div>
                </div>
            </FadeIn>

            {/* ── Recent Pipeline Runs ─────────────────── */}
            <FadeIn delay={0.35}>
                <div className="card">
                    <div className="section-title">
                        <span className="dot"></span>
                        Recent Pipeline Executions
                        <span className="section-subtitle">{totalRuns} total runs</span>
                    </div>
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Run ID</th>
                                    <th>Status</th>
                                    <th>Started</th>
                                    <th>Finished</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(runs as any[])?.slice(0, 6).map((r: any, idx: number) => (
                                    <tr key={r.run_id || r.id || `run-${idx}`}>
                                        <td className="mono">{(r.run_id ?? r.id ?? '\u2014').toString().slice(0, 12)}...</td>
                                        <td>
                                            <span className={`status-dot ${r.status}`}></span>
                                            <span style={{ fontWeight: 500, color: r.status === 'succeeded' ? 'var(--color-success)' : r.status === 'failed' ? 'var(--color-danger)' : 'var(--color-info)' }}>
                                                {r.status}
                                            </span>
                                        </td>
                                        <td>{r.started_at ? formatTunisDateTime(r.started_at) : r.created_at ?? '\u2014'}</td>
                                        <td>{formatTunisDateTime(r.finished_at)}</td>
                                    </tr>
                                )) || <tr><td colSpan={4} className="empty-state-text">No pipeline runs</td></tr>}
                            </tbody>
                        </table>
                    </div>
                </div>
            </FadeIn>
        </div>
    );
}
