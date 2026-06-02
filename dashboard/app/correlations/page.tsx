import { api } from '../../lib/api';
import CorrelationHeatmap from '../../components/CorrelationHeatmap';
import PageInfoBar from '../../components/PageInfoBar';

export const dynamic = 'force-dynamic';

export default async function CorrelationsPage() {
    const data = await api.correlation();

    const pearson = data?.filter((c: any) => c.method === 'pearson') ?? [];
    const spearman = data?.filter((c: any) => c.method === 'spearman') ?? [];
    const strongCorrs = data?.filter((c: any) => Math.abs(c.corr_value) >= 0.7).length ?? 0;
    const significantCorrs = data?.filter((c: any) => c.p_value < 0.05).length ?? 0;

    // Surface the single strongest signal for the hero — the "headline" insight
    const top = [...(data ?? [])].sort((a: any, b: any) => Math.abs(b.corr_value) - Math.abs(a.corr_value))[0];
    const headline = top
        ? `${top.metric_x.replace(/^mean_/, '')} ↔ ${top.metric_y.replace(/^mean_/, '')} (ρ ${top.corr_value >= 0 ? '+' : ''}${top.corr_value.toFixed(2)})`
        : '—';

    return (
        <div className="grid" style={{ gap: 20 }}>
            <PageInfoBar
                eyebrow="OSS ↔ CEM Convergence"
                description="Does a bad cell actually cost us revenue? This page quantifies the link between network KPIs (latency, throughput, packet loss) and customer-facing outcomes (churn risk, data usage, revenue) using Pearson + Spearman. Anything with |ρ| ≥ 0.7 and p < 0.05 is an actionable business lever."
                values={[
                    { text: `${strongCorrs} strong relationships (|ρ| ≥ 0.7)` },
                    { text: `${significantCorrs} statistically significant (p < 0.05)` },
                    { text: `Top signal: ${headline}` },
                ]}
            />

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

            <CorrelationHeatmap data={data ?? []} />

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
                                <th>Metric Y (CEM)</th>
                                <th>Method</th>
                                <th>ρ</th>
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
