"use client";

interface CellSeverityBucket {
    label: string;
    key: 'low' | 'warning' | 'critical';
    color: string;
    bgColor: string;
}

const SEVERITY_BUCKETS: CellSeverityBucket[] = [
    { label: 'Low', key: 'low', color: 'var(--color-success)', bgColor: '52, 211, 153' },
    { label: 'Warning', key: 'warning', color: 'var(--color-warning)', bgColor: '251, 191, 36' },
    { label: 'Critical', key: 'critical', color: 'var(--color-danger)', bgColor: '248, 113, 113' },
];

function getBucket(severity: number): 'low' | 'warning' | 'critical' {
    if (severity > 0.9) return 'critical';
    if (severity > 0.5) return 'warning';
    return 'low';
}

function getBucketData(ossData: any[]) {
    const matrix = new Map<string, { low: number; warning: number; critical: number; maxSev: number }>();

    for (const item of ossData ?? []) {
        const cell = item?.cell_id ?? 'UNKNOWN';
        const sev = Number(item?.severity ?? 0);
        if (!matrix.has(cell)) {
            matrix.set(cell, { low: 0, warning: 0, critical: 0, maxSev: 0 });
        }
        const entry = matrix.get(cell)!;
        entry[getBucket(sev)] += 1;
        entry.maxSev = Math.max(entry.maxSev, sev);
    }

    const rows = Array.from(matrix.entries())
        .map(([cell, counts]) => ({
            cell,
            counts,
            total: counts.low + counts.warning + counts.critical,
            maxSev: counts.maxSev,
        }))
        .sort((a, b) => b.total - a.total)
        .slice(0, 12);

    const maxCount = rows.reduce((max, row) => {
        return Math.max(max, row.counts.low, row.counts.warning, row.counts.critical);
    }, 0);

    return { rows, maxCount };
}

export default function AnomalyHeatmap({ ossData }: { ossData: any[] }) {
    const { rows, maxCount } = getBucketData(ossData ?? []);

    if (rows.length === 0) {
        return (
            <div className="heatmap-empty">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--text-muted)', opacity: 0.4 }}>
                    <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18" /><path d="M9 3v18" />
                </svg>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 12 }}>No OSS anomaly data available for heatmap</div>
            </div>
        );
    }

    const totalAnomalies = rows.reduce((s, r) => s + r.total, 0);
    const criticalCells = rows.filter(r => r.counts.critical > 0).length;

    return (
        <div className="heatmap-container">
            {/* Summary bar */}
            <div className="heatmap-summary">
                <div className="heatmap-summary-item">
                    <span className="heatmap-summary-value">{rows.length}</span>
                    <span className="heatmap-summary-label">Cells</span>
                </div>
                <div className="heatmap-summary-item">
                    <span className="heatmap-summary-value">{totalAnomalies}</span>
                    <span className="heatmap-summary-label">Anomalies</span>
                </div>
                <div className="heatmap-summary-item">
                    <span className="heatmap-summary-value" style={{ color: criticalCells > 0 ? 'var(--color-danger)' : 'var(--color-success)' }}>{criticalCells}</span>
                    <span className="heatmap-summary-label">Critical Cells</span>
                </div>
                <div className="heatmap-legend">
                    {SEVERITY_BUCKETS.map(b => (
                        <div key={b.key} className="heatmap-legend-item">
                            <div className="heatmap-legend-swatch" style={{ background: b.color }} />
                            <span>{b.label}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Grid */}
            <div className="heatmap-grid">
                {/* Header row */}
                <div className="heatmap-row heatmap-header">
                    <div className="heatmap-cell-label">Cell ID</div>
                    {SEVERITY_BUCKETS.map(b => (
                        <div key={b.key} className="heatmap-col-header" style={{ color: b.color }}>{b.label}</div>
                    ))}
                    <div className="heatmap-col-header" style={{ color: 'var(--text-secondary)' }}>Total</div>
                </div>

                {/* Data rows */}
                {rows.map((row, rowIdx) => (
                    <div key={row.cell} className="heatmap-row" style={{ animationDelay: `${rowIdx * 40}ms` }}>
                        <div className="heatmap-cell-label">
                            <span className="mono">{row.cell}</span>
                            {row.counts.critical > 0 && (
                                <span className="heatmap-cell-alert">
                                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M12 2L1 21h22L12 2zm0 4l7.53 13H4.47L12 6z"/><rect x="11" y="10" width="2" height="4"/><rect x="11" y="16" width="2" height="2"/>
                                    </svg>
                                </span>
                            )}
                        </div>
                        {SEVERITY_BUCKETS.map(bucket => {
                            const value = row.counts[bucket.key];
                            const intensity = maxCount > 0 ? value / maxCount : 0;
                            const alpha = value > 0 ? Math.max(0.15, Math.min(0.85, 0.15 + intensity * 0.7)) : 0.04;
                            return (
                                <div
                                    key={`${row.cell}-${bucket.key}`}
                                    className="heatmap-tile"
                                    style={{
                                        background: `rgba(${bucket.bgColor}, ${alpha})`,
                                        borderColor: value > 0 ? `rgba(${bucket.bgColor}, ${Math.min(0.5, alpha + 0.15)})` : 'var(--border)',
                                        color: value > 0 ? bucket.color : 'var(--text-muted)',
                                    }}
                                    title={`${row.cell} — ${bucket.label}: ${value} anomalies`}
                                >
                                    {value}
                                </div>
                            );
                        })}
                        <div className="heatmap-total">
                            {row.total}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
