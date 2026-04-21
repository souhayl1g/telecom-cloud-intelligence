import { api } from '../../lib/api';
import PageInfoBar from '../../components/PageInfoBar';

export const dynamic = 'force-dynamic';

/* -- Horizontal bar chart component ---------------------------------------- */
function CapacityBar({ label, used, total, unit, thresholdPct = 80 }: {
    label: string; used: number; total: number; unit: string; thresholdPct?: number;
}) {
    const pct = total > 0 ? (used / total) * 100 : 0;
    const color = pct >= 90 ? 'var(--color-danger)' : pct >= thresholdPct ? 'var(--color-warning)' : 'var(--color-success)';
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{label}</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', color }}>
                    {used.toLocaleString(undefined, { maximumFractionDigits: 1 })} / {total.toLocaleString()} {unit} ({pct.toFixed(1)}%)
                </span>
            </div>
            <div style={{ height: 8, background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${Math.min(pct, 100)}%`, background: color, borderRadius: 4, transition: 'width 0.5s ease' }} />
            </div>
        </div>
    );
}

/* -- Ring chart ------------------------------------------------------------ */
function RingChart({ value, max, label, color, size = 100 }: {
    value: number; max: number; label: string; color: string; size?: number;
}) {
    const pct = Math.min(value / max, 1);
    const r = (size - 12) / 2;
    const circ = 2 * Math.PI * r;
    const offset = circ * (1 - pct);
    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
            <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="6" />
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="6"
                    strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 1s ease' }} />
            </svg>
            <div style={{ marginTop: -(size / 2 + 10), position: 'relative', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color, fontFamily: 'JetBrains Mono, monospace' }}>
                    {(pct * 100).toFixed(0)}%
                </div>
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: size / 2 - 20 }}>
                {label}
            </div>
        </div>
    );
}

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export default async function CapacityPage() {
    const [kpiData, infraData, sla] = await Promise.all([
        api.kpiSummary(),
        api.infraStats(),
        api.slaRisk(),
    ]);

    const kpiHistory = ((kpiData as any[]) ?? []).reverse();
    const infra = infraData as any;
    const slaScore = (sla as any)?.score ?? 0;

    // Real row counts from PostgreSQL
    const rowCounts = infra?.row_counts ?? {};
    const totalRows = infra?.total_rows ?? 0;
    const totalDataRows = infra?.total_data_rows ?? 0;
    const dbSizeMb = infra?.db_size_mb ?? 0;
    const dbSizeBytes = infra?.db_size_bytes ?? 0;
    const tableSizes = infra?.table_sizes ?? {};
    const pipelineTiming = infra?.pipeline_timing ?? {};
    const dataLakeLayers = infra?.data_lake_layers ?? [];

    // Real KPI averages from SLA model explanation->input_features
    const avgThroughput = kpiHistory.length > 0
        ? kpiHistory.reduce((s: number, k: any) => s + (Number(k.avg_throughput) || 0), 0) / kpiHistory.length
        : 0;
    const avgUsers = kpiHistory.length > 0
        ? kpiHistory.reduce((s: number, k: any) => s + (Number(k.avg_users) || 0), 0) / kpiHistory.length
        : 0;
    const avgLatency = kpiHistory.length > 0
        ? kpiHistory.reduce((s: number, k: any) => s + (Number(k.avg_latency) || 0), 0) / kpiHistory.length
        : 0;
    const avgPacketLoss = kpiHistory.length > 0
        ? kpiHistory.reduce((s: number, k: any) => s + (Number(k.avg_packet_loss) || 0), 0) / kpiHistory.length
        : 0;

    // Capacity references from observed peaks (1.5x headroom)
    const maxThroughput = kpiHistory.length > 0
        ? Math.ceil(Math.max(...kpiHistory.map((k: any) => Number(k.avg_throughput) || 0)) * 1.5)
        : 200;
    const maxUsersPerCell = kpiHistory.length > 0
        ? Math.ceil(Math.max(...kpiHistory.map((k: any) => Number(k.avg_users) || 0)) * 1.5)
        : 800;
    const maxLatencyBudget = 50; // ms — standard telecom SLA target

    // Real storage: actual PostgreSQL size, with realistic DB capacity
    const dbCapacityMb = 500; // PostgreSQL single-instance reasonable working set
    const dbPct = dbSizeMb > 0 ? (dbSizeMb / dbCapacityMb) * 100 : 0;

    // Real compute: pipeline duration as fraction of cycle time (120s)
    const cycleSec = 120;
    const avgPipelineSec = pipelineTiming.avg_duration_sec || 0;
    const computePct = avgPipelineSec > 0 ? (avgPipelineSec / cycleSec) * 100 : (slaScore * 40 + 10);

    const networkPct = maxThroughput > 0 ? (avgThroughput / maxThroughput) * 100 : 0;
    const userPct = maxUsersPerCell > 0 ? (avgUsers / maxUsersPerCell) * 100 : 0;

    // Growth rate from real KPI trend
    let monthlyGrowthRate = 0.05;
    if (kpiHistory.length >= 4) {
        const half = Math.floor(kpiHistory.length / 2);
        const firstHalf = kpiHistory.slice(0, half);
        const secondHalf = kpiHistory.slice(half);
        const avgFirst = firstHalf.reduce((s: number, k: any) => s + (Number(k.avg_users) || 0), 0) / firstHalf.length;
        const avgSecond = secondHalf.reduce((s: number, k: any) => s + (Number(k.avg_users) || 0), 0) / secondHalf.length;
        if (avgFirst > 0) {
            const rawGrowth = (avgSecond - avgFirst) / avgFirst;
            monthlyGrowthRate = Math.max(0.01, Math.min(0.20, Math.abs(rawGrowth)));
        }
    }

    const monthsToCapacity = (resource: number) => {
        let current = resource;
        let months = 0;
        while (current < 90 && months < 24) {
            current *= (1 + monthlyGrowthRate);
            months++;
        }
        return months;
    };

    const networkCapMonths = monthsToCapacity(networkPct);
    const userCapMonths = monthsToCapacity(userPct);
    const storageCapMonths = monthsToCapacity(dbPct);
    const hasRealData = kpiHistory.length > 0;

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Planning · HCS Scaling Blueprint"
                description="When do we run out of room? Live utilization of network throughput, compute (pipeline duration vs 120s cycle), subscriber density and PostgreSQL storage is measured against observed peaks; projected growth tells you how many months before each resource hits 90%. The output is a concrete HCS ECS/OBS/RDS scaling recommendation."
                values={[
                    { text: `Network ${networkPct.toFixed(0)}% · Compute ${computePct.toFixed(0)}% · DB ${dbPct.toFixed(0)}%` },
                    { text: `Growth rate: ${(monthlyGrowthRate * 100).toFixed(1)}%/mo${kpiHistory.length >= 4 ? ' (observed)' : ' (estimated)'}` },
                    { text: `Next constraint: ${Math.min(networkCapMonths, userCapMonths, storageCapMonths)} mo to 90%` },
                ]}
            />

            {/* Utilization Ring Charts */}
            <div className="grid grid-4">
                <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 16px' }}>
                    <RingChart value={networkPct} max={100} label="Network" color={networkPct > 80 ? 'var(--color-danger)' : networkPct > 60 ? 'var(--color-warning)' : 'var(--color-success)'} />
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>Avg {avgThroughput.toFixed(1)} / {maxThroughput} Mbps</div>
                </div>
                <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 16px' }}>
                    <RingChart value={computePct} max={100} label="Compute" color={computePct > 80 ? 'var(--color-danger)' : computePct > 60 ? 'var(--color-warning)' : 'var(--color-info)'} />
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
                        {avgPipelineSec > 0 ? `${avgPipelineSec.toFixed(0)}s / ${cycleSec}s cycle` : 'Pipeline timing N/A'}
                    </div>
                </div>
                <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 16px' }}>
                    <RingChart value={userPct} max={100} label="Subscribers" color={userPct > 80 ? 'var(--color-danger)' : userPct > 60 ? 'var(--color-warning)' : 'var(--color-success)'} />
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>Avg {avgUsers.toFixed(0)} / {maxUsersPerCell} per cell</div>
                </div>
                <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 16px' }}>
                    <RingChart value={dbPct} max={100} label="Database" color={dbPct > 80 ? 'var(--color-danger)' : 'var(--color-info)'} />
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>{dbSizeMb.toFixed(1)} MB / {dbCapacityMb} MB</div>
                </div>
            </div>

            {/* Detailed Resource Bars */}
            <div className="grid grid-2">
                <div className="card">
                    <div className="section-title">
                        <span className="dot"></span>
                        Infrastructure Utilization
                        <span className="section-subtitle">Live from PostgreSQL + pipeline</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <CapacityBar label="Network Throughput" used={avgThroughput} total={maxThroughput} unit="Mbps" />
                        <CapacityBar label="Active Users / Cell" used={avgUsers} total={maxUsersPerCell} unit="users" />
                        <CapacityBar label="Latency Budget" used={avgLatency} total={maxLatencyBudget} unit="ms" />
                        <CapacityBar label="PostgreSQL Database" used={dbSizeMb} total={dbCapacityMb} unit="MB" />
                        <CapacityBar label="PostgreSQL Rows" used={totalRows} total={totalRows * 5} unit="rows" thresholdPct={70} />
                        <CapacityBar label="Pipeline Compute" used={computePct} total={100} unit="%" />
                    </div>
                </div>

                <div className="card">
                    <div className="section-title">
                        <span className="dot"></span>
                        Growth Projections
                        <span className="section-subtitle">At {(monthlyGrowthRate * 100).toFixed(1)}% estimated growth{kpiHistory.length >= 4 ? ' (computed from data)' : ' (default estimate)'}</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <div style={{ padding: '14px 16px', background: networkCapMonths <= 6 ? 'var(--color-warning-bg)' : 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: `1px solid ${networkCapMonths <= 6 ? 'var(--color-warning-border)' : 'var(--border)'}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: 13 }}>Network Capacity</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Time to 90% utilization</div>
                                </div>
                                <div style={{ fontSize: 20, fontWeight: 700, color: networkCapMonths <= 6 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                    {networkCapMonths >= 24 ? '24+' : networkCapMonths} mo
                                </div>
                            </div>
                        </div>
                        <div style={{ padding: '14px 16px', background: userCapMonths <= 6 ? 'var(--color-warning-bg)' : 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: `1px solid ${userCapMonths <= 6 ? 'var(--color-warning-border)' : 'var(--border)'}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: 13 }}>Subscriber Capacity</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Time to 90% utilization</div>
                                </div>
                                <div style={{ fontSize: 20, fontWeight: 700, color: userCapMonths <= 6 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                    {userCapMonths >= 24 ? '24+' : userCapMonths} mo
                                </div>
                            </div>
                        </div>
                        <div style={{ padding: '14px 16px', background: storageCapMonths <= 6 ? 'var(--color-warning-bg)' : 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: `1px solid ${storageCapMonths <= 6 ? 'var(--color-warning-border)' : 'var(--border)'}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: 13 }}>Database Capacity</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Time to 90% utilization</div>
                                </div>
                                <div style={{ fontSize: 20, fontWeight: 700, color: storageCapMonths <= 6 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                    {storageCapMonths >= 24 ? '24+' : storageCapMonths} mo
                                </div>
                            </div>
                        </div>

                        <div style={{ padding: '12px 16px', background: 'var(--color-info-bg)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-info-border)', fontSize: 11, color: 'var(--text-secondary)' }}>
                            <strong>AI Recommendation:</strong> {networkCapMonths <= 12 || userCapMonths <= 12
                                ? 'Capacity constraints approaching within 12 months. Plan infrastructure scaling: consider HCS ECS autoscaling groups and OBS tiered storage for data lake expansion.'
                                : 'Current capacity is sufficient for projected 12-month growth. Continue monitoring and reassess quarterly.'
                            }
                        </div>
                    </div>
                </div>
            </div>

            {/* Real PostgreSQL Table Breakdown */}
            <div className="grid grid-2">
                <div className="card">
                    <div className="section-title">
                        <span className="dot"></span>
                        PostgreSQL Table Breakdown
                        <span className="section-subtitle">{totalRows.toLocaleString()} total rows, {dbSizeMb} MB</span>
                    </div>
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Table</th>
                                    <th style={{ textAlign: 'right' }}>Rows</th>
                                    <th style={{ textAlign: 'right' }}>Size</th>
                                </tr>
                            </thead>
                            <tbody>
                                {[
                                    { name: 'anomalies', rows: rowCounts.anomalies, size: tableSizes.anomalies_bytes },
                                    { name: 'correlation_insights', rows: rowCounts.correlations, size: tableSizes.correlations_bytes },
                                    { name: 'sla_risk_scores', rows: rowCounts.sla_scores, size: tableSizes.sla_bytes },
                                    { name: 'revenue_anomalies', rows: rowCounts.revenue_anomalies, size: tableSizes.revenue_bytes },
                                    { name: 'dataset_registry', rows: rowCounts.datasets, size: tableSizes.datasets_bytes },
                                    { name: 'pipeline_runs', rows: rowCounts.pipeline_runs, size: tableSizes.pipeline_bytes },
                                    { name: 'agent_actions', rows: rowCounts.actions, size: 0 },
                                    { name: 'users', rows: rowCounts.users, size: 0 },
                                ].sort((a, b) => (b.rows || 0) - (a.rows || 0)).map((t, i) => (
                                    <tr key={i}>
                                        <td className="mono" style={{ fontSize: 11 }}>{t.name}</td>
                                        <td className="mono" style={{ textAlign: 'right' }}>{(t.rows || 0).toLocaleString()}</td>
                                        <td style={{ textAlign: 'right', fontSize: 11, color: 'var(--text-muted)' }}>
                                            {t.size ? formatBytes(t.size) : '-'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="card">
                    <div className="section-title">
                        <span className="dot"></span>
                        Data Lake (MinIO) Layers
                        <span className="section-subtitle">{totalDataRows.toLocaleString()} total data rows</span>
                    </div>
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Layer</th>
                                    <th style={{ textAlign: 'right' }}>Datasets</th>
                                    <th style={{ textAlign: 'right' }}>Rows</th>
                                </tr>
                            </thead>
                            <tbody>
                                {dataLakeLayers.map((l: any, i: number) => (
                                    <tr key={i}>
                                        <td>
                                            <span className={`badge ${l.layer === 'raw' ? 'badge-info' : l.layer === 'processed' ? 'badge-warning' : 'badge-success'}`} style={{ fontSize: 9 }}>
                                                {(l.layer || '').toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="mono" style={{ textAlign: 'right' }}>{(l.datasets || 0).toLocaleString()}</td>
                                        <td className="mono" style={{ textAlign: 'right' }}>{(l.rows || 0).toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Pipeline Timing */}
                    <div style={{ marginTop: 16, padding: '14px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Pipeline Performance</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                                <span>Finished Runs</span>
                                <span className="mono" style={{ fontWeight: 600 }}>{(pipelineTiming.finished_runs || 0).toLocaleString()}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                                <span>Avg Duration</span>
                                <span className="mono" style={{ fontWeight: 600 }}>
                                    {avgPipelineSec > 0 ? `${avgPipelineSec.toFixed(1)}s` : 'N/A'}
                                </span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                                <span>Max Duration</span>
                                <span className="mono" style={{ fontWeight: 600 }}>
                                    {(pipelineTiming.max_duration_sec || 0) > 0 ? `${pipelineTiming.max_duration_sec}s` : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* KPI History from Real Pipeline Data */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    KPI History (from ML Model Features)
                    <span className="section-subtitle">{kpiHistory.length} pipeline runs</span>
                </div>
                {!hasRealData ? (
                    <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                        No pipeline data yet. Run the pipeline to populate real KPI metrics.
                    </div>
                ) : (
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Run Time</th>
                                    <th>SLA Score</th>
                                    <th>Throughput (Mbps)</th>
                                    <th>Latency (ms)</th>
                                    <th>Users</th>
                                    <th>Packet Loss (%)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {kpiHistory.slice(-10).reverse().map((k: any, i: number) => {
                                    const score = Number(k.score) || 0;
                                    return (
                                        <tr key={i}>
                                            <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                                {new Date(k.created_at).toLocaleString()}
                                            </td>
                                            <td>
                                                <span style={{ color: score >= 0.7 ? 'var(--color-danger)' : score >= 0.4 ? 'var(--color-warning)' : 'var(--color-success)', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>
                                                    {score.toFixed(3)}
                                                </span>
                                            </td>
                                            <td className="mono">{(Number(k.avg_throughput) || 0).toFixed(1)}</td>
                                            <td className="mono">{(Number(k.avg_latency) || 0).toFixed(1)}</td>
                                            <td className="mono">{Math.round(Number(k.avg_users) || 0)}</td>
                                            <td className="mono">{(Number(k.avg_packet_loss) || 0).toFixed(2)}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* HCS Mapping */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    HCS Cloud Scaling Recommendations
                    <span className="section-subtitle">Huawei Cloud Stack mapping</span>
                </div>
                <div className="grid grid-3" style={{ gap: 12 }}>
                    <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Compute (ECS)</div>
                        <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 4 }}>
                            Pipeline: {computePct.toFixed(1)}% of cycle
                        </div>
                        <div style={{ fontSize: 11, color: computePct > 70 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                            {computePct > 70
                                ? 'Scale up to 8 vCPU / 16 GB recommended'
                                : 'Current allocation sufficient'
                            }
                        </div>
                    </div>
                    <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Storage (OBS)</div>
                        <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 4 }}>
                            MinIO {'\u2192'} OBS migration
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--color-info)' }}>
                            {totalDataRows.toLocaleString()} data rows across {dataLakeLayers.reduce((s: number, l: any) => s + (l.datasets || 0), 0)} datasets
                        </div>
                    </div>
                    <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Database (RDS)</div>
                        <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 4 }}>
                            PostgreSQL 16 on RDS
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--color-success)' }}>
                            {totalRows.toLocaleString()} rows, {dbSizeMb} MB used
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
