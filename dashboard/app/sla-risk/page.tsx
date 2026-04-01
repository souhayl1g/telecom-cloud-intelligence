import { api } from '../../lib/api';
import SlaChart from '../../components/SlaChart';
import RiskGauge from '../../components/RiskGauge';

export const dynamic = 'force-dynamic';

export default async function SLARiskPage() {
    const [sla, data] = await Promise.all([api.slaRisk(), api.slaRiskHistory()]);
    const history = data ?? [];

    // Stats
    const scores = history.map((r: any) => r.score).filter((s: any) => typeof s === 'number');
    const avg = scores.length > 0 ? scores.reduce((a: number, b: number) => a + b, 0) / scores.length : 0;
    const max = scores.length > 0 ? Math.max(...scores) : 0;
    const min = scores.length > 0 ? Math.min(...scores) : 0;

    return (
        <div className="grid" style={{ gap: 24 }}>
            <div className="page-header">
                <h1>SLA Risk Analysis</h1>
                <p>GradientBoostingRegressor prediction of SLA breach probability from 9 aggregated KPI features</p>
            </div>

            {/* Summary */}
            <div className="summary-strip">
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-purple)' }}>{(sla as any)?.score?.toFixed(3) ?? '\u2014'}</div>
                        <div className="summary-item-label">Current Risk</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value">{avg.toFixed(3)}</div>
                        <div className="summary-item-label">Average</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-danger)' }}>{max.toFixed(3)}</div>
                        <div className="summary-item-label">Peak Risk</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-success)' }}>{min.toFixed(3)}</div>
                        <div className="summary-item-label">Lowest</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value">{history.length}</div>
                        <div className="summary-item-label">Data Points</div>
                    </div>
                </div>
            </div>

            {/* Gauge + Chart */}
            <div className="grid grid-2">
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot"></span>
                        Current Risk Level
                    </div>
                    <RiskGauge
                        score={(sla as any)?.score ?? 0}
                        region={(sla as any)?.region}
                        modelVersion={(sla as any)?.model_version}
                    />

                    {/* Feature importances from explanation */}
                    {(sla as any)?.explanation?.feature_importances && (
                        <div style={{ marginTop: 20 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                Feature Importances
                            </div>
                            {Object.entries((sla as any).explanation.feature_importances)
                                .sort(([, a]: any, [, b]: any) => b - a)
                                .map(([feat, imp]: [string, any]) => (
                                    <div key={feat} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                                        <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 150, textAlign: 'right' }}>{feat}</span>
                                        <div style={{ flex: 1, height: 5, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
                                            <div style={{ height: '100%', width: `${imp * 100}%`, background: 'var(--gradient-brand)', borderRadius: 3 }} />
                                        </div>
                                        <span className="mono" style={{ fontSize: 11, minWidth: 40 }}>{(imp * 100).toFixed(1)}%</span>
                                    </div>
                                ))
                            }
                        </div>
                    )}
                </div>
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot"></span>
                        Risk Score Trend
                        <span className="section-subtitle">Threshold lines at 0.4 / 0.7</span>
                    </div>
                    <SlaChart data={history} />
                </div>
            </div>

            {/* History Table */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    Score History
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Score</th>
                                <th>Risk Level</th>
                                <th>Region</th>
                                <th>Model</th>
                                <th>Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history.map((r: any, idx: number) => {
                                const score = r.score ?? 0;
                                let level = { cls: 'badge-success', label: 'HEALTHY' };
                                if (score >= 0.7) level = { cls: 'badge-danger', label: 'CRITICAL' };
                                else if (score >= 0.4) level = { cls: 'badge-warning', label: 'WARNING' };
                                return (
                                    <tr key={idx}>
                                        <td style={{ color: 'var(--text-muted)' }}>{idx + 1}</td>
                                        <td>
                                            <span className="mono" style={{
                                                fontWeight: 600,
                                                color: score >= 0.7 ? 'var(--color-danger)' : score >= 0.4 ? 'var(--color-warning)' : 'var(--color-success)'
                                            }}>
                                                {score.toFixed(4)}
                                            </span>
                                        </td>
                                        <td><span className={`badge ${level.cls}`}>{level.label}</span></td>
                                        <td>{r.region ?? '\u2014'}</td>
                                        <td className="mono" style={{ fontSize: 12 }}>{r.model_version ?? 'v2.0'}</td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{r.created_at ? new Date(r.created_at).toLocaleString() : '\u2014'}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
