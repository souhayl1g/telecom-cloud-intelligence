"use client";

interface Correlation {
    metric_x: string;
    metric_y: string;
    method: string;
    corr_value: number;
    p_value: number;
    run_id?: string;
    region?: string;
}

function getCorrColor(v: number): string {
    const abs = Math.abs(v);
    if (abs >= 0.7) return v > 0 ? 'var(--color-success)' : 'var(--color-danger)';
    if (abs >= 0.4) return v > 0 ? '#86efac' : 'var(--color-warning)';
    return 'var(--text-muted)';
}

function getCorrBg(v: number): string {
    const abs = Math.abs(v);
    if (abs >= 0.7) return v > 0 ? 'var(--color-success-bg)' : 'var(--color-danger-bg)';
    if (abs >= 0.4) return v > 0 ? 'rgba(134, 239, 172, 0.08)' : 'var(--color-warning-bg)';
    return 'rgba(255,255,255,0.03)';
}

function getStrengthLabel(v: number): string {
    const abs = Math.abs(v);
    const dir = v >= 0 ? '+' : '-';
    if (abs >= 0.7) return `Strong ${dir}`;
    if (abs >= 0.4) return `Moderate ${dir}`;
    if (abs >= 0.2) return `Weak ${dir}`;
    return 'Negligible';
}

export default function CorrelationHeatmap({ data }: { data: Correlation[] }) {
    if (!data || data.length === 0) {
        return <div className="empty-state"><div className="empty-state-text">No correlation data available</div></div>;
    }

    // Split by method
    const pearson = data.filter(d => d.method === 'pearson');
    const spearman = data.filter(d => d.method === 'spearman');
    const display = pearson.length > 0 ? pearson : data;

    return (
        <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
                {display.map((c, i) => {
                    const v = c.corr_value;
                    return (
                        <div key={i} style={{
                            background: getCorrBg(v),
                            border: `1px solid ${v >= 0.4 || v <= -0.4 ? getCorrColor(v) : 'var(--border)'}`,
                            borderRadius: 'var(--radius-md)',
                            padding: '14px',
                            transition: 'all 0.2s',
                        }}>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                {c.metric_x}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
                                vs {c.metric_y}
                            </div>
                            <div style={{ fontSize: 22, fontWeight: 700, color: getCorrColor(v), letterSpacing: -1, fontFamily: "'JetBrains Mono', monospace" }}>
                                {v >= 0 ? '+' : ''}{v.toFixed(3)}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 10, color: 'var(--text-muted)' }}>
                                <span style={{ color: getCorrColor(v), fontWeight: 600 }}>{getStrengthLabel(v)}</span>
                                <span>p={c.p_value < 0.001 ? '<0.001' : c.p_value.toFixed(3)}</span>
                            </div>
                        </div>
                    );
                })}
            </div>
            {spearman.length > 0 && (
                <details style={{ marginTop: 16 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 13, color: 'var(--text-secondary)', fontWeight: 600, padding: '8px 0' }}>
                        Spearman Rank Correlations ({spearman.length} pairs)
                    </summary>
                    <div className="table-container" style={{ marginTop: 8 }}>
                        <table className="table">
                            <thead>
                                <tr><th>Metric X</th><th>Metric Y</th><th>Correlation</th><th>Strength</th><th>p-value</th></tr>
                            </thead>
                            <tbody>
                                {spearman.map((c, i) => (
                                    <tr key={i}>
                                        <td style={{ fontWeight: 500 }}>{c.metric_x}</td>
                                        <td style={{ fontWeight: 500 }}>{c.metric_y}</td>
                                        <td><span className="mono" style={{ color: getCorrColor(c.corr_value) }}>{c.corr_value >= 0 ? '+' : ''}{c.corr_value.toFixed(3)}</span></td>
                                        <td><span style={{ color: getCorrColor(c.corr_value), fontSize: 12, fontWeight: 600 }}>{getStrengthLabel(c.corr_value)}</span></td>
                                        <td className="mono">{c.p_value < 0.001 ? '<0.001' : c.p_value.toFixed(4)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </details>
            )}
        </div>
    );
}
