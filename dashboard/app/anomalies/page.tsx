import { api } from '../../lib/api';
import ScoreBar from '../../components/ScoreBar';
import AnomalyHeatmap from '../../components/AnomalyHeatmap';

export const dynamic = 'force-dynamic';

function getSeverityBadge(severity: number) {
    if (severity > 0.9) return { cls: 'badge-danger', label: 'CRITICAL' };
    if (severity > 0.5) return { cls: 'badge-warning', label: 'WARNING' };
    return { cls: 'badge-success', label: 'LOW' };
}

export default async function AnomaliesPage() {
    const [oss, bss] = await Promise.all([api.anomalies(), api.revenueAnomalies()]);

    const ossCritical = oss?.filter((a: any) => a.severity > 0.9).length ?? 0;
    const ossWarning = oss?.filter((a: any) => a.severity > 0.5 && a.severity <= 0.9).length ?? 0;
    const ossLow = (oss?.length ?? 0) - ossCritical - ossWarning;
    const bssHigh = bss?.filter((b: any) => (b.severity ?? b.score) > 0.8).length ?? 0;

    return (
        <div className="grid" style={{ gap: 24 }}>
            <div className="page-header">
                <h1>Anomaly Detection</h1>
                <p>IsolationForest-powered anomaly detection across OSS network KPIs and BSS revenue streams</p>
            </div>

            {/* Summary Strip */}
            <div className="summary-strip">
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-danger)' }}>{ossCritical}</div>
                        <div className="summary-item-label">OSS Critical</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-warning)' }}>{ossWarning}</div>
                        <div className="summary-item-label">OSS Warning</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-success)' }}>{ossLow}</div>
                        <div className="summary-item-label">OSS Low</div>
                    </div>
                </div>
                <div style={{ width: 1, background: 'var(--border)', margin: '0 8px' }} />
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-purple)' }}>{bss?.length ?? 0}</div>
                        <div className="summary-item-label">BSS Total</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-danger)' }}>{bssHigh}</div>
                        <div className="summary-item-label">BSS High Impact</div>
                    </div>
                </div>
            </div>

            {/* OSS Anomalies */}
            <div className="card card-accent-top">
                <div className="section-title">
                    <span className="dot"></span>
                    OSS Cell Severity Heatmap
                    <span className="section-subtitle">Top 12 cells by anomaly concentration</span>
                </div>
                <AnomalyHeatmap ossData={oss ?? []} />
            </div>

            {/* OSS Anomalies */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    OSS Network Anomalies
                    <span className="section-subtitle">{oss?.length ?? 0} detected &middot; IsolationForest v2.0</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Cell ID</th>
                                <th>KPI</th>
                                <th>Severity</th>
                                <th>Score</th>
                                <th>Value</th>
                                <th>Baseline</th>
                                <th>Region</th>
                                <th>Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            {oss?.slice(0, 50).map((a: any, idx: number) => {
                                const badge = getSeverityBadge(a.severity ?? 0);
                                return (
                                    <tr key={idx}>
                                        <td className="mono">{a.cell_id ?? '\u2014'}</td>
                                        <td style={{ fontWeight: 500 }}>{a.kpi_name ?? 'composite'}</td>
                                        <td><span className={`badge ${badge.cls}`}>{badge.label}</span></td>
                                        <td><ScoreBar value={a.severity ?? 0} /></td>
                                        <td className="mono">{a.value != null ? Number(a.value).toFixed(2) : '\u2014'}</td>
                                        <td className="mono" style={{ color: 'var(--text-muted)' }}>{a.baseline_value != null ? Number(a.baseline_value).toFixed(2) : '\u2014'}</td>
                                        <td>{a.region ?? '\u2014'}</td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{a.created_at ? new Date(a.created_at).toLocaleString() : a.ts ?? '\u2014'}</td>
                                    </tr>
                                );
                            }) || <tr><td colSpan={8}>No data</td></tr>}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* BSS Revenue Anomalies */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    BSS Revenue Anomalies
                    <span className="section-subtitle">{bss?.length ?? 0} detected &middot; IsolationForest v2.0</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Subscriber</th>
                                <th>Operator</th>
                                <th>Type</th>
                                <th>Plan</th>
                                <th>Metric</th>
                                <th>Severity</th>
                                <th>Score</th>
                                <th>Value</th>
                                <th>Region</th>
                                <th>Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            {bss?.slice(0, 50).map((a: any, idx: number) => {
                                const sev = a.severity ?? a.score ?? 0;
                                const badge = getSeverityBadge(sev);
                                return (
                                    <tr key={idx}>
                                        <td className="mono" style={{ maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.subscriber_id ? a.subscriber_id.slice(0, 10) + '...' : 'masked'}</td>
                                        <td style={{ fontWeight: 500 }}>{a.operator ?? '\u2014'}</td>
                                        <td>
                                            <span className={`badge ${a.line_type === 'prepaid' ? 'badge-info' : 'badge-purple'}`}>
                                                {a.line_type ?? '\u2014'}
                                            </span>
                                        </td>
                                        <td style={{ fontSize: 12 }}>{a.plan ?? '\u2014'}</td>
                                        <td style={{ fontWeight: 500 }}>{a.metric_name ?? 'composite'}</td>
                                        <td><span className={`badge ${badge.cls}`}>{badge.label}</span></td>
                                        <td><ScoreBar value={sev} /></td>
                                        <td className="mono">{a.value != null ? Number(a.value).toFixed(2) : '\u2014'}</td>
                                        <td>{a.region ?? '\u2014'}</td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{a.created_at ? new Date(a.created_at).toLocaleString() : a.ts ?? '\u2014'}</td>
                                    </tr>
                                );
                            }) || <tr><td colSpan={10}>No data</td></tr>}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
