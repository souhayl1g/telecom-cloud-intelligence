import Link from 'next/link';
import { api } from '../../lib/api';
import SlaChart from '../../components/SlaChart';
import AnomaliesBarChart from '../../components/AnomaliesBarChart';
import RiskGauge from '../../components/RiskGauge';

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

    // Severity breakdown
    const ossCritical = anomalies?.filter((a: any) => a.severity > 0.9).length ?? 0;
    const ossWarning = anomalies?.filter((a: any) => a.severity > 0.5 && a.severity <= 0.9).length ?? 0;
    const strongCorrs = correlations?.filter((c: any) => Math.abs(c.corr_value) >= 0.7).length ?? 0;

    // Agent status
    const slaScore = (sla as any)?.score ?? 0;
    const agentHealth = slaScore >= 0.7 ? 'critical' : slaScore >= 0.4 ? 'warning' : 'healthy';
    const pendingActions = (ossCritical > 0 ? 1 : 0) + (slaScore >= 0.4 ? 1 : 0) + ((revenue as any[])?.filter((r: any) => (r.severity ?? 0) > 0.8).length > 0 ? 1 : 0);

    return (
        <div className="grid" style={{ gap: 24 }}>
            {/* Page Header */}
            <div className="page-header">
                <h1>Operations Overview</h1>
                <p>Real-time AI-powered intelligence across OSS and BSS domains</p>
            </div>

            {/* KPI Strip - clickable cards */}
            <div className="grid grid-4">
                <Link href="/sla-risk" className="card card-compact overview-kpi-link">
                    <div className="stat-card">
                        <div className="stat-icon purple">{'\u26A1'}</div>
                        <div className="stat-content">
                            <div className="stat-label">SLA Risk Score</div>
                            <div className="stat-value" style={{
                                color: slaScore >= 0.7 ? 'var(--color-danger)' : slaScore >= 0.4 ? 'var(--color-warning)' : 'var(--color-success)'
                            }}>
                                {slaScore?.toFixed(3) ?? '\u2014'}
                            </div>
                            <div className="stat-sub">GradientBoosting v2.0</div>
                        </div>
                        <span className="overview-kpi-arrow">{'\u2192'}</span>
                    </div>
                </Link>
                <Link href="/anomalies" className="card card-compact overview-kpi-link">
                    <div className="stat-card">
                        <div className="stat-icon danger">{'\u2687'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Total Anomalies</div>
                            <div className="stat-value">{totalAnomalies}</div>
                            <div className="stat-sub">{ossCount} OSS + {bssCount} BSS</div>
                        </div>
                        <span className="overview-kpi-arrow">{'\u2192'}</span>
                    </div>
                </Link>
                <Link href="/pipeline-runs" className="card card-compact overview-kpi-link">
                    <div className="stat-card">
                        <div className="stat-icon success">{'\u25B6'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Pipeline Success</div>
                            <div className="stat-value">{successRate}%</div>
                            <div className="stat-sub">{successRuns}/{totalRuns} runs succeeded</div>
                        </div>
                        <span className="overview-kpi-arrow">{'\u2192'}</span>
                    </div>
                </Link>
                <Link href="/correlations" className="card card-compact overview-kpi-link">
                    <div className="stat-card">
                        <div className="stat-icon cyan">{'\u2194'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Correlations</div>
                            <div className="stat-value">{corrCount}</div>
                            <div className="stat-sub">{strongCorrs} strong | OSS{'\u2194'}BSS</div>
                        </div>
                        <span className="overview-kpi-arrow">{'\u2192'}</span>
                    </div>
                </Link>
            </div>

            {/* L4 Agent Status Banner */}
            <Link href="/l4-agent" className="overview-agent-banner">
                <div className="overview-agent-left">
                    <div className="overview-agent-dot" />
                    <div>
                        <div className="overview-agent-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline', verticalAlign: '-2px', marginRight: 6, color: '#ffd700' }}><rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1"/></svg>
                    L4 Autonomous Agent
                    <span className="overview-ai-badge">
                        <span className="overview-ai-badge-dot" />
                        Qwen2.5 7B
                    </span>
                </div>
                        <div className="overview-agent-sub">
                            {agentHealth === 'critical'
                                ? `CRITICAL: ${ossCritical} critical anomalies, SLA risk at ${slaScore.toFixed(3)} \u2014 agent has ${pendingActions} pending actions`
                                : agentHealth === 'warning'
                                ? `WARNING: SLA risk at ${slaScore.toFixed(3)} \u2014 agent monitoring ${pendingActions} situation(s)`
                                : `HEALTHY: All systems nominal \u2014 agent monitoring ${totalAnomalies} anomalies across domains`
                            }
                        </div>
                    </div>
                </div>
                <div className="overview-agent-right">
                    <span className={`badge badge-${agentHealth === 'critical' ? 'danger' : agentHealth === 'warning' ? 'warning' : 'success'}`}>
                        {agentHealth.toUpperCase()}
                    </span>
                    <span className="overview-agent-arrow">{'\u2192'} Open Workspace</span>
                </div>
            </Link>

            {/* SLA Risk Gauge + SLA Trend */}
            <div className="grid grid-2">
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot"></span>
                        SLA Breach Risk
                        <span className="section-subtitle">GradientBoostingRegressor</span>
                    </div>
                    <RiskGauge
                        score={(sla as any)?.score ?? 0}
                        region={(sla as any)?.region}
                        modelVersion={(sla as any)?.model_version}
                    />
                </div>
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot"></span>
                        SLA Risk Trend
                        <span className="section-subtitle">Last {hist?.length ?? 0} runs</span>
                    </div>
                    <SlaChart data={hist || []} />
                </div>
            </div>

            {/* Anomaly Distribution + Model Info */}
            <div className="grid grid-2">
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
                        <Link href="/model-evaluation" style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--brand-primary)', fontWeight: 500 }}>View Evaluation {'\u2192'}</Link>
                    </div>
                    <div className="model-info" style={{ flexDirection: 'column' }}>
                        <div className="model-chip">
                            <span className="model-chip-icon">{'\u26A1'}</span>
                            <div>
                                <div className="model-chip-name">SLA Risk Predictor</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>GradientBoostingRegressor &middot; 9 features</div>
                            </div>
                            <span className="model-chip-version badge-success badge">v2.0</span>
                        </div>
                        <div className="model-chip">
                            <span className="model-chip-icon">{'\u2687'}</span>
                            <div>
                                <div className="model-chip-name">OSS Anomaly Detector</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>IsolationForest &middot; 5 KPI features</div>
                            </div>
                            <span className="model-chip-version badge-info badge">v2.0</span>
                        </div>
                        <div className="model-chip">
                            <span className="model-chip-icon">{'\u2661'}</span>
                            <div>
                                <div className="model-chip-name">BSS Revenue Anomaly</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>IsolationForest &middot; revenue + usage</div>
                            </div>
                            <span className="model-chip-version badge-purple badge">v2.0</span>
                        </div>
                    </div>

                    {/* Anomaly Alert Summary */}
                    <div style={{ marginTop: 20, padding: '14px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 10 }}>ALERT SUMMARY</div>
                        <div style={{ display: 'flex', gap: 16 }}>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-danger)' }}>{ossCritical}</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Critical (&gt;0.9)</div>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-warning)' }}>{ossWarning}</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Warning (0.5-0.9)</div>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-success)' }}>{ossCount - ossCritical - ossWarning}</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Low (&lt;0.5)</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Recent Pipeline Runs */}
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
                            {(runs as any[])?.slice(0, 8).map((r: any, idx: number) => (
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
        </div>
    );
}
