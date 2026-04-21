"use client";
import { useMemo, useState } from 'react';

interface Correlation {
    metric_x: string;
    metric_y: string;
    method: string;
    corr_value: number;
    p_value: number;
    run_id?: string;
    region?: string;
}

/* Diverging RdBu scale — blue for negative, white for 0, red for positive.
 * Matches scientific correlation-matrix convention. */
function getDivergingColor(v: number): string {
    // Clamp to [-1, 1]
    const t = Math.max(-1, Math.min(1, v));
    if (t >= 0) {
        // 0 → neutral-grey, 1 → deep red (#C7000B Huawei crimson)
        const r = 240 + Math.round(t * (199 - 240));    // 240 → 199
        const g = 240 + Math.round(t * (0 - 240));      // 240 → 0
        const b = 240 + Math.round(t * (11 - 240));     // 240 → 11
        return `rgba(${r}, ${g}, ${b}, ${0.25 + Math.abs(t) * 0.7})`;
    }
    // negative → deep blue
    const r = 240 + Math.round(Math.abs(t) * (37 - 240));
    const g = 240 + Math.round(Math.abs(t) * (99 - 240));
    const b = 240 + Math.round(Math.abs(t) * (235 - 240));
    return `rgba(${r}, ${g}, ${b}, ${0.25 + Math.abs(t) * 0.7})`;
}

function getTextColor(v: number): string {
    return Math.abs(v) > 0.55 ? '#fff' : 'var(--text-primary)';
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
    const [hovered, setHovered] = useState<Correlation | null>(null);

    const { xMetrics, yMetrics, cellMap, pearson, spearman } = useMemo(() => {
        const pearson = data.filter((d) => d.method === 'pearson');
        const spearman = data.filter((d) => d.method === 'spearman');
        const source = pearson.length > 0 ? pearson : data;
        const xs = Array.from(new Set(source.map((d) => d.metric_x)));
        const ys = Array.from(new Set(source.map((d) => d.metric_y)));
        const cellMap = new Map<string, Correlation>();
        for (const c of source) cellMap.set(`${c.metric_x}::${c.metric_y}`, c);
        return { xMetrics: xs, yMetrics: ys, cellMap, pearson, spearman };
    }, [data]);

    if (!data || data.length === 0) {
        return <div className="empty-state"><div className="empty-state-text">No correlation data available</div></div>;
    }

    const short = (s: string) =>
        s.replace(/^mean_/, '').replace(/_ms$/, '').replace(/_mbps$/, '').replace(/_pct$/, '').replace(/_tnd$/, '').replace(/_gb$/, '');

    return (
        <div>
            <div className="corr-heatmap-wrap">
                <div className="corr-heatmap-header">
                    <div>
                        <div className="corr-heatmap-title">
                            <span className="corr-heatmap-title-dot" />
                            OSS ↔ BSS Correlation Matrix
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                            Rows = Network KPIs (OSS) · Columns = Customer KPIs (BSS) · {pearson.length} Pearson pairs
                        </div>
                    </div>
                    <div className="corr-heatmap-legend">
                        <span>−1</span>
                        <div className="corr-heatmap-gradient" />
                        <span>+1</span>
                    </div>
                </div>

                <div
                    className="corr-heatmap-grid"
                    style={{
                        gridTemplateColumns: `160px repeat(${yMetrics.length}, minmax(96px, 1fr))`,
                    }}
                >
                    {/* Header row */}
                    <div />
                    {yMetrics.map((y) => (
                        <div key={`h-${y}`} className="corr-heatmap-axis" title={y} style={{ textAlign: 'center' }}>
                            {short(y)}
                        </div>
                    ))}

                    {/* Data rows */}
                    {xMetrics.map((x) => (
                        <>
                            <div key={`l-${x}`} className="corr-heatmap-axis" title={x} style={{ textAlign: 'right' }}>
                                {short(x)}
                            </div>
                            {yMetrics.map((y) => {
                                const c = cellMap.get(`${x}::${y}`);
                                if (!c) return <div key={`${x}-${y}`} />;
                                return (
                                    <div
                                        key={`${x}-${y}`}
                                        className="corr-heatmap-cell"
                                        style={{
                                            background: getDivergingColor(c.corr_value),
                                            color: getTextColor(c.corr_value),
                                            outline: hovered === c ? '2px solid var(--brand-secondary)' : 'none',
                                        }}
                                        onMouseEnter={() => setHovered(c)}
                                        onMouseLeave={() => setHovered(null)}
                                        title={`${c.metric_x} ↔ ${c.metric_y}\n${c.corr_value.toFixed(3)} (p=${c.p_value < 0.001 ? '<0.001' : c.p_value.toFixed(3)})`}
                                    >
                                        {c.corr_value >= 0 ? '+' : ''}{c.corr_value.toFixed(2)}
                                    </div>
                                );
                            })}
                        </>
                    ))}
                </div>

                {hovered && (
                    <div style={{ marginTop: 14, padding: 12, borderRadius: 'var(--radius-md)', background: 'var(--bg-elevated)', border: '1px solid var(--border)', fontSize: 12 }}>
                        <div style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>
                            <strong style={{ color: 'var(--text-primary)' }}>{hovered.metric_x}</strong> ↔ <strong style={{ color: 'var(--text-primary)' }}>{hovered.metric_y}</strong>
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                            ρ = <span className="mono" style={{ color: 'var(--text-primary)' }}>{hovered.corr_value.toFixed(4)}</span>
                            {' · '}p = <span className="mono">{hovered.p_value < 0.001 ? '<0.001' : hovered.p_value.toFixed(4)}</span>
                            {' · '}<span>{getStrengthLabel(hovered.corr_value)}</span>
                            {' · '}method: <span>{hovered.method}</span>
                        </div>
                    </div>
                )}
            </div>

            {spearman.length > 0 && (
                <details style={{ marginTop: 16 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 13, color: 'var(--text-secondary)', fontWeight: 600, padding: '8px 0' }}>
                        Spearman Rank Correlations ({spearman.length} pairs)
                    </summary>
                    <div className="table-container" style={{ marginTop: 8 }}>
                        <table className="table">
                            <thead>
                                <tr><th>Metric X</th><th>Metric Y</th><th>ρ</th><th>Strength</th><th>p-value</th></tr>
                            </thead>
                            <tbody>
                                {spearman.map((c, i) => (
                                    <tr key={i}>
                                        <td style={{ fontWeight: 500 }}>{c.metric_x}</td>
                                        <td style={{ fontWeight: 500 }}>{c.metric_y}</td>
                                        <td><span className="mono">{c.corr_value >= 0 ? '+' : ''}{c.corr_value.toFixed(3)}</span></td>
                                        <td><span style={{ fontSize: 12, fontWeight: 600 }}>{getStrengthLabel(c.corr_value)}</span></td>
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
