import Link from 'next/link';
import { api } from '../../lib/api';
import SlaChart from '../../components/SlaChart';
import AnomaliesBarChart from '../../components/AnomaliesBarChart';
import RiskGauge from '../../components/RiskGauge';
import { StaggerGrid, StaggerItem, FadeIn, SlideInBanner } from '../../components/OverviewAnimations';
import PageInfoBar from '../../components/PageInfoBar';

export const dynamic = 'force-dynamic';

export default async function OverviewPage() {
    const [sla, hist, anomalies, revenue, runs, correlations] = await Promise.all([
        api.slaRisk(),
        api.slaRiskHistory(),
        api.anomalies(),
        api.revenueAnomalies(),
        api.pipelineRuns(),
        api.correlation(),
    ]);

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

    const slaScore = (sla as any)?.score ?? 0;
    const agentHealth = slaScore >= 0.7 ? 'critical' : slaScore >= 0.4 ? 'warning' : 'healthy';
    const pendingActions = (ossCritical > 0 ? 1 : 0) + (slaScore >= 0.4 ? 1 : 0) + ((revenue as any[])?.filter((r: any) => (r.severity ?? 0) > 0.8).length > 0 ? 1 : 0);

    return (
        <div className="dash-grid">
            <PageInfoBar
                eyebrow="Cloud-Native AI Operations · Live"
                description="Live OSS+BSS intelligence platform for Tunisie Telecom, running on Huawei Cloud Stack. Detects anomalies and SLA risk in real time, correlates network KPIs with customer-experience outcomes, and drives closed-loop autonomous operations via the L4 Agent."
                values={[
                    { text: '3 ML models — SLA risk, OSS anomalies, BSS fraud' },
                    { text: 'OSS ↔ BSS correlation engine (Pearson + Spearman)' },
                    { text: 'ADN Level-4 autonomous remediation playbooks' },
                ]}
            />

            {/* ── KPI Cards Row ─────────────────────────── */}
            <StaggerGrid className="dash-kpi-row">
                <StaggerItem>
                    <Link href="/sla-risk" className="dash-kpi-card">
                        <div className="dash-kpi-icon dash-kpi-icon-red">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                                <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
                            </svg>
                        </div>
                        <div className="dash-kpi-content">
                            <span className="dash-kpi-label">SLA Risk Score</span>
                            <span className="dash-kpi-value" style={{
                                color: slaScore >= 0.7 ? 'var(--color-danger)' : slaScore >= 0.4 ? 'var(--color-warning)' : 'var(--color-success)'
                            }}>
                                {slaScore?.toFixed(3) ?? '\u2014'}
                            </span>
                            <span className="dash-kpi-sub">GradientBoosting v2.0</span>
                        </div>
                        <div className="dash-kpi-trend dash-kpi-trend-up">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /></svg>
                        </div>
                    </Link>
                </StaggerItem>

                <StaggerItem>
                    <Link href="/anomalies" className="dash-kpi-card">
                        <div className="dash-kpi-icon dash-kpi-icon-orange">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                            </svg>
                        </div>
                        <div className="dash-kpi-content">
                            <span className="dash-kpi-label">Total Anomalies</span>
                            <span className="dash-kpi-value">{totalAnomalies}</span>
                            <span className="dash-kpi-sub">{ossCount} OSS + {bssCount} BSS</span>
                        </div>
                        <div className="dash-kpi-mini-bar">
                            <div className="dash-kpi-mini-fill" style={{ width: `${Math.min(100, totalAnomalies * 2)}%` }} />
                        </div>
                    </Link>
                </StaggerItem>

                <StaggerItem>
                    <Link href="/pipeline-runs" className="dash-kpi-card">
                        <div className="dash-kpi-icon dash-kpi-icon-green">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
                            </svg>
                        </div>
                        <div className="dash-kpi-content">
                            <span className="dash-kpi-label">Pipeline Success</span>
                            <span className="dash-kpi-value">{successRate}<span className="dash-kpi-unit">%</span></span>
                            <span className="dash-kpi-sub">{successRuns}/{totalRuns} runs succeeded</span>
                        </div>
                        <div className="dash-kpi-ring">
                            <svg viewBox="0 0 36 36" width="40" height="40">
                                <circle cx="18" cy="18" r="15" fill="none" stroke="var(--border)" strokeWidth="3" />
                                <circle cx="18" cy="18" r="15" fill="none" stroke="var(--color-success)" strokeWidth="3"
                                    strokeDasharray={`${successRate * 0.94} 100`}
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
                            <span className="dash-kpi-sub">{strongCorrs} strong | OSS{'\u2194'}BSS</span>
                        </div>
                    </Link>
                </StaggerItem>
            </StaggerGrid>

            {/* ── Main Charts Row (2/3 + 1/3 like reference) ─── */}
            <FadeIn delay={0.15}>
                <div className="dash-main-row">
                    {/* Left: SLA Trend (large chart) */}
                    <div className="dash-chart-main card">
                        <div className="dash-chart-header">
                            <div>
                                <div className="section-title" style={{ marginBottom: 2 }}>
                                    <span className="dot"></span>
                                    SLA Risk Trend
                                </div>
                                <span className="dash-chart-period">Last {hist?.length ?? 0} pipeline runs</span>
                            </div>
                            <div className="dash-chart-actions">
                                <button className="dash-time-btn dash-time-active">All</button>
                                <button className="dash-time-btn">24h</button>
                                <button className="dash-time-btn">7d</button>
                            </div>
                        </div>
                        <SlaChart data={hist || []} />
                    </div>

                    {/* Right: Risk Gauge + Alert Summary */}
                    <div className="dash-chart-side">
                        <div className="card">
                            <div className="section-title" style={{ marginBottom: 4 }}>
                                <span className="dot"></span>
                                Breach Risk
                            </div>
                            <RiskGauge
                                score={(sla as any)?.score ?? 0}
                                region={(sla as any)?.region}
                                modelVersion={(sla as any)?.model_version}
                            />
                        </div>
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
                                    ? `CRITICAL: ${ossCritical} critical anomalies, SLA risk at ${slaScore.toFixed(3)} \u2014 ${pendingActions} pending actions`
                                    : agentHealth === 'warning'
                                    ? `WARNING: SLA risk at ${slaScore.toFixed(3)} \u2014 monitoring ${pendingActions} situation(s)`
                                    : `All systems nominal \u2014 monitoring ${totalAnomalies} anomalies across domains`
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

            {/* ── Bottom Row: Anomaly Distribution + AI Models ─── */}
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
                                <div className="dash-model-dot" style={{ background: 'var(--color-danger)' }} />
                                <div className="dash-model-info">
                                    <span className="dash-model-name">SLA Risk Predictor</span>
                                    <span className="dash-model-desc">GradientBoostingRegressor &middot; 9 features</span>
                                </div>
                                <span className="badge badge-success">v2.0</span>
                            </div>
                            <div className="dash-model-item">
                                <div className="dash-model-dot" style={{ background: 'var(--color-info)' }} />
                                <div className="dash-model-info">
                                    <span className="dash-model-name">OSS Anomaly Detector</span>
                                    <span className="dash-model-desc">IsolationForest &middot; 5 KPI features</span>
                                </div>
                                <span className="badge badge-info">v2.0</span>
                            </div>
                            <div className="dash-model-item">
                                <div className="dash-model-dot" style={{ background: 'var(--color-purple)' }} />
                                <div className="dash-model-info">
                                    <span className="dash-model-name">BSS Revenue Anomaly</span>
                                    <span className="dash-model-desc">IsolationForest &middot; revenue + usage</span>
                                </div>
                                <span className="badge badge-purple">v2.0</span>
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
                                    <tr key={idx}>
                                        <td className="mono">{(r.run_id ?? r.id ?? '\u2014').toString().slice(0, 12)}...</td>
                                        <td>
                                            <span className={`status-dot ${r.status}`}></span>
                                            <span style={{ fontWeight: 500, color: r.status === 'succeeded' ? 'var(--color-success)' : r.status === 'failed' ? 'var(--color-danger)' : 'var(--color-info)' }}>
                                                {r.status}
                                            </span>
                                        </td>
                                        <td>{r.started_at ? new Date(r.started_at).toLocaleString() : r.created_at ?? '\u2014'}</td>
                                        <td>{r.finished_at ? new Date(r.finished_at).toLocaleString() : '\u2014'}</td>
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
