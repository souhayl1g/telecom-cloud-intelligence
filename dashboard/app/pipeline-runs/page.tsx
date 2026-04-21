import { api } from '../../lib/api';
import PageInfoBar from '../../components/PageInfoBar';

export const dynamic = 'force-dynamic';

export default async function PipelineRunsPage() {
    const data = await api.pipelineRuns() as any[] | null;
    const runs = data ?? [];

    const succeeded = runs.filter(r => r.status === 'succeeded').length;
    const failed = runs.filter(r => r.status === 'failed').length;
    const total = runs.length;
    const successRate = total > 0 ? Math.round((succeeded / total) * 100) : 0;

    // Calculate average duration for runs that have both timestamps
    const durations = runs
        .filter(r => r.started_at && r.finished_at)
        .map(r => (new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()) / 1000);
    const avgDuration = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Pipeline · 2-min Cadence"
                description="Is the platform actually running? Every 2 minutes the worker executes the 22-step ETL: ingest OSS + BSS → stage to MinIO (raw/processed/curated) → run 3 ML models → compute OSS↔BSS correlations → persist to PostgreSQL. This page is the audit trail for each cycle."
                values={[
                    { text: `${total} runs · ${successRate}% success rate` },
                    { text: `${succeeded} succeeded · ${failed} failed` },
                    { text: `Avg duration: ${avgDuration.toFixed(1)}s per cycle` },
                ]}
            />

            {/* Stats */}
            <div className="grid grid-4">
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon info">{'\u25B6'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Total Runs</div>
                            <div className="stat-value">{total}</div>
                        </div>
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon success">{'\u2713'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Success Rate</div>
                            <div className="stat-value">{successRate}%</div>
                            <div className="stat-sub">{succeeded} succeeded</div>
                        </div>
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon danger">{'\u2717'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Failed</div>
                            <div className="stat-value">{failed}</div>
                        </div>
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon cyan">{'\u23F1'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Avg Duration</div>
                            <div className="stat-value">{avgDuration > 0 ? `${avgDuration.toFixed(1)}s` : '\u2014'}</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Pipeline visual */}
            <div className="card" style={{ padding: '18px 24px' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    Pipeline Stages (22 Steps)
                </div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
                    {[
                        { label: 'Buckets', color: 'var(--color-info)' },
                        { label: 'OSS Gen', color: 'var(--color-info)' },
                        { label: 'BSS Gen', color: 'var(--color-info)' },
                        { label: 'Upload Raw', color: 'var(--color-cyan)' },
                        { label: 'Register', color: 'var(--color-cyan)' },
                        { label: 'Process OSS', color: 'var(--color-purple)' },
                        { label: 'Process BSS', color: 'var(--color-purple)' },
                        { label: 'KPI Agg', color: 'var(--color-warning)' },
                        { label: 'SLA Risk', color: 'var(--color-danger)' },
                        { label: 'OSS Anomaly', color: 'var(--color-danger)' },
                        { label: 'BSS Anomaly', color: 'var(--color-danger)' },
                        { label: 'Correlate', color: 'var(--color-success)' },
                        { label: 'Curate', color: 'var(--color-success)' },
                        { label: 'Persist', color: 'var(--color-success)' },
                    ].map((stage, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <div style={{
                                padding: '4px 10px',
                                borderRadius: 'var(--radius-sm)',
                                background: `color-mix(in srgb, ${stage.color} 15%, transparent)`,
                                border: `1px solid color-mix(in srgb, ${stage.color} 30%, transparent)`,
                                color: stage.color,
                                fontSize: 10,
                                fontWeight: 600,
                                whiteSpace: 'nowrap',
                            }}>
                                {stage.label}
                            </div>
                            {i < 13 && <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{'\u2192'}</span>}
                        </div>
                    ))}
                </div>
            </div>

            {/* Table */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    Run History
                    <span className="section-subtitle">{total} executions</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Run ID</th>
                                <th>Status</th>
                                <th>Started</th>
                                <th>Finished</th>
                                <th>Duration</th>
                                <th>Error</th>
                            </tr>
                        </thead>
                        <tbody>
                            {runs.map((r: any, idx: number) => {
                                const duration = r.started_at && r.finished_at
                                    ? ((new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()) / 1000).toFixed(1) + 's'
                                    : '\u2014';
                                return (
                                    <tr key={idx}>
                                        <td style={{ color: 'var(--text-muted)' }}>{idx + 1}</td>
                                        <td className="mono">{(r.run_id ?? r.id ?? '\u2014').toString().slice(0, 16)}...</td>
                                        <td>
                                            <span className={`status-dot ${r.status}`}></span>
                                            <span style={{
                                                fontWeight: 600,
                                                color: r.status === 'succeeded' ? 'var(--color-success)' : r.status === 'failed' ? 'var(--color-danger)' : 'var(--color-info)'
                                            }}>
                                                {r.status}
                                            </span>
                                        </td>
                                        <td style={{ fontSize: 12 }}>{r.started_at ? new Date(r.started_at).toLocaleString() : '\u2014'}</td>
                                        <td style={{ fontSize: 12 }}>{r.finished_at ? new Date(r.finished_at).toLocaleString() : '\u2014'}</td>
                                        <td className="mono">{duration}</td>
                                        <td style={{ fontSize: 12, color: 'var(--color-danger)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {r.error_message || '\u2014'}
                                        </td>
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
