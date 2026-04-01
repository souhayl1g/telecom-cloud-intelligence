import { api } from '../../lib/api';
import CorrelationHeatmap from '../../components/CorrelationHeatmap';

export const dynamic = 'force-dynamic';

export default async function CorrelationsPage() {
    const data = await api.correlation();

    // Get unique metric pairs count
    const pearson = data?.filter((c: any) => c.method === 'pearson') ?? [];
    const spearman = data?.filter((c: any) => c.method === 'spearman') ?? [];
    const strongCorrs = data?.filter((c: any) => Math.abs(c.corr_value) >= 0.7).length ?? 0;
    const significantCorrs = data?.filter((c: any) => c.p_value < 0.05).length ?? 0;

    return (
        <div className="grid" style={{ gap: 24 }}>
            <div className="page-header">
                <h1>OSS \u2194 BSS Correlation Analysis</h1>
                <p>Pearson and Spearman correlation between network performance (OSS) and business metrics (BSS) — demonstrating O+B convergence</p>
            </div>

            {/* Summary */}
            <div className="summary-strip">
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value">{data?.length ?? 0}</div>
                        <div className="summary-item-label">Total Correlations</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value">{pearson.length}</div>
                        <div className="summary-item-label">Pearson</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value">{spearman.length}</div>
                        <div className="summary-item-label">Spearman</div>
                    </div>
                </div>
                <div style={{ width: 1, background: 'var(--border)', margin: '0 8px' }} />
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-success)' }}>{strongCorrs}</div>
                        <div className="summary-item-label">Strong (|r|&ge;0.7)</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-info)' }}>{significantCorrs}</div>
                        <div className="summary-item-label">Significant (p&lt;0.05)</div>
                    </div>
                </div>
            </div>

            {/* Correlation Heatmap */}
            <div className="card card-accent-top">
                <div className="section-title">
                    <span className="dot"></span>
                    Pearson Correlation Matrix
                    <span className="section-subtitle">{pearson.length} metric pairs</span>
                </div>
                <CorrelationHeatmap data={data ?? []} />
            </div>

            {/* Full Table */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    All Correlation Results
                    <span className="section-subtitle">Sorted by strength</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Metric X (OSS)</th>
                                <th>Metric Y (BSS)</th>
                                <th>Method</th>
                                <th>Correlation</th>
                                <th>Strength</th>
                                <th>p-value</th>
                                <th>Significant</th>
                                <th>Region</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data?.sort((a: any, b: any) => Math.abs(b.corr_value) - Math.abs(a.corr_value)).map((c: any, idx: number) => {
                                const abs = Math.abs(c.corr_value);
                                const dir = c.corr_value >= 0 ? '+' : '-';
                                let strengthLabel = 'Negligible';
                                let strengthColor = 'var(--text-muted)';
                                if (abs >= 0.7) { strengthLabel = `Strong ${dir}`; strengthColor = c.corr_value > 0 ? 'var(--color-success)' : 'var(--color-danger)'; }
                                else if (abs >= 0.4) { strengthLabel = `Moderate ${dir}`; strengthColor = c.corr_value > 0 ? '#86efac' : 'var(--color-warning)'; }
                                else if (abs >= 0.2) { strengthLabel = `Weak ${dir}`; strengthColor = 'var(--text-secondary)'; }
                                const sig = c.p_value < 0.05;

                                return (
                                    <tr key={idx}>
                                        <td style={{ fontWeight: 500 }}>{c.metric_x}</td>
                                        <td style={{ fontWeight: 500 }}>{c.metric_y}</td>
                                        <td><span className={`badge ${c.method === 'pearson' ? 'badge-info' : 'badge-purple'}`}>{c.method}</span></td>
                                        <td>
                                            <span className="mono" style={{ color: strengthColor, fontWeight: 600 }}>
                                                {c.corr_value >= 0 ? '+' : ''}{c.corr_value.toFixed(4)}
                                            </span>
                                        </td>
                                        <td><span style={{ color: strengthColor, fontWeight: 600, fontSize: 12 }}>{strengthLabel}</span></td>
                                        <td className="mono">{c.p_value < 0.001 ? '<0.001' : c.p_value.toFixed(4)}</td>
                                        <td>
                                            {sig
                                                ? <span className="badge badge-success">YES</span>
                                                : <span className="badge badge-neutral">NO</span>
                                            }
                                        </td>
                                        <td>{c.region ?? '\u2014'}</td>
                                    </tr>
                                );
                            }) || <tr><td colSpan={8}>No data</td></tr>}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
