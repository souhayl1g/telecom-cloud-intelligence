import { api } from '../../lib/api';
import ScoreBar from '../../components/ScoreBar';
import PageInfoBar from '../../components/PageInfoBar';

export const dynamic = 'force-dynamic';

/* ── Helpers ──────────────────────────────────────────────────────────── */
function formatTs(ts: string | undefined) {
    if (!ts) return '\u2014';
    return new Date(ts).toLocaleString();
}

/* ── Architecture diagram node ────────────────────────────────────────── */
function ArchNode({ icon, label, sub, color }: { icon: string; label: string; sub: string; color: string }) {
    return (
        <div className="dwh-arch-node">
            <div className="dwh-arch-icon" style={{ background: `var(--color-${color}-bg)`, borderColor: `var(--color-${color}-border)` }}>
                {icon}
            </div>
            <div className="dwh-arch-label">{label}</div>
            <div className="dwh-arch-sub">{sub}</div>
        </div>
    );
}

export default async function DataWarehousePage() {
    const [oss, bss, corrs, runs, cem, vae, rat] = await Promise.all([
        api.anomalies(),
        api.cemAnomalies(),
        api.correlation(),
        api.pipelineRuns(),
        api.cemScores(),
        api.vaeAnomalies(),
        api.ratUnderservice(),
    ]);

    const ossData = oss ?? [];
    const bssData = bss ?? [];
    const corrData = corrs ?? [];
    const runData = (runs as any[]) ?? [];
    const cemData = cem ?? [];
    const vaeData = vae ?? [];
    const ratData = rat ?? [];

    const totalRecords = ossData.length + bssData.length + corrData.length + runData.length + (Array.isArray(cemData) ? cemData.length : 0) + (Array.isArray(vaeData) ? vaeData.length : 0) + (Array.isArray(ratData) ? ratData.length : 0);

    // Get the most recent timestamp across all datasets
    const allTimestamps = [
        ...ossData.map((a: any) => a.created_at),
        ...bssData.map((a: any) => a.created_at),
        ...runData.map((r: any) => r.finished_at || r.started_at),
    ].filter(Boolean).map(t => new Date(t).getTime());
    const lastUpdated = allTimestamps.length > 0 ? new Date(Math.max(...allTimestamps)).toLocaleString() : 'N/A';

    // Table definitions — all PostgreSQL tables in the platform
    const tables = [
        {
            id: 'oss_cell_kpis',
            name: 'oss_cell_kpis',
            layer: 'Raw Data',
            layerColor: 'info',
            description: 'Real OSS cell KPIs from Tunisie Telecom (18.8M rows) — throughput, latency, RSRP, cell load per RAT',
            records: 18805773,
            columns: ['cell_id', 'area', 'rat_type', 'throughput_mbps', 'latency_ms', 'packet_loss_rate', 'rsrp_dbm', 'active_users', 'anomaly_flag', 'timestamp'],
            source: 'Huawei U2000',
        },
        {
            id: 'bss_subscribers',
            name: 'bss_subscribers',
            layer: 'Raw Data',
            layerColor: 'info',
            description: 'Real BSS subscriber CEM profiles (968K rows) — device, RAT usage, attach success rates',
            records: 968077,
            columns: ['imsi_hash', 'tac', 'generation', 'highest_rat', 'area', 'dou_total', 'traffic_2g', 'traffic_3g', 'traffic_4g', 'traffic_5g', 's1_mme_sr'],
            source: 'SmartCare CEM',
        },
        {
            id: 'subscriber_features',
            name: 'subscriber_features',
            layer: 'Processed',
            layerColor: 'purple',
            description: 'Derived subscriber features — CEM score, RAT gap, churn risk, network experience index',
            records: 2468026,
            columns: ['imsi_hash', 'cem_score', 'rat_gap_score', 'churn_risk_flag', 'network_experience_index', 'usim_bottleneck'],
            source: 'Feature Engineering',
        },
        {
            id: 'area_network_health',
            name: 'area_network_health',
            layer: 'Processed',
            layerColor: 'purple',
            description: 'Area-level network health aggregates — avg throughput, latency, anomaly count, subscriber density',
            records: 312,
            columns: ['area', 'avg_throughput', 'avg_latency', 'avg_packet_loss', 'anomaly_count', 'subscriber_count', 'avg_cem_score', 'underserved_pct'],
            source: 'Feature Engineering',
        },
        {
            id: 'cem_scores',
            name: 'cem_scores',
            layer: 'Processed',
            layerColor: 'success',
            description: 'CEM v3 inference results — LightGBM DART subscriber experience scores',
            records: Array.isArray(cemData) ? cemData.length : 0,
            columns: ['imsi_hash', 'cem_score', 'area', 'generation', 'created_at'],
            source: 'ML Pipeline v3',
        },
        {
            id: 'rat_underservice_scores',
            name: 'rat_underservice_scores',
            layer: 'Processed',
            layerColor: 'warning',
            description: 'RAT v3 inference results — XGBoost GPU underservice detection per subscriber',
            records: Array.isArray(ratData) ? ratData.length : 0,
            columns: ['imsi_hash', 'rat_gap_score', 'underserved_flag', 'area', 'generation', 'created_at'],
            source: 'ML Pipeline v3',
        },
        {
            id: 'vae_anomaly_scores',
            name: 'vae_anomaly_scores',
            layer: 'Processed',
            layerColor: 'info',
            description: 'VAE v3 inference results — PyTorch VAE anomaly detection on OSS cell KPIs',
            records: Array.isArray(vaeData) ? vaeData.length : 0,
            columns: ['cell_id', 'area', 'reconstruction_error', 'anomaly_flag', 'throughput_mbps', 'latency_ms', 'created_at'],
            source: 'ML Pipeline v3',
        },
        {
            id: 'granger_causality_results',
            name: 'granger_causality_results',
            layer: 'Processed',
            layerColor: 'cyan',
            description: 'Granger causality engine output — temporal OSS→BSS causal pairs with optimal lag and significance',
            records: corrData.length * 3, // estimated
            columns: ['oss_metric', 'bss_metric', 'optimal_lag', 'p_value', 'significant', 'created_at'],
            source: 'Granger Engine',
        },
        {
            id: 'corr',
            name: 'oss_bss_correlations',
            layer: 'Processed',
            layerColor: 'purple',
            description: 'Statistical correlations between network and business metrics (Pearson/Spearman)',
            records: corrData.length,
            columns: ['metric_x', 'metric_y', 'method', 'corr_value', 'p_value', 'region'],
            source: 'Correlation Engine',
        },
        {
            id: 'runs',
            name: 'pipeline_runs',
            layer: 'Operational',
            layerColor: 'success',
            description: 'Data pipeline execution history and status tracking',
            records: runData.length,
            columns: ['run_id', 'status', 'started_at', 'finished_at', 'error_message'],
            source: 'Orchestrator',
        },
    ];

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Data Lake · Raw · Processed · Curated"
                description="What's physically sitting in the platform? Browse every CEM score, VAE anomaly, RAT underservice flag, correlation, Granger causality result and pipeline run across the 3-layer data lake (MinIO raw → processed → curated) and the PostgreSQL tables behind them. This is the receipt for every insight shown elsewhere."
                values={[
                    { text: `${totalRecords.toLocaleString()} total records across ${tables.length} tables` },
                    { text: `${runData.length} pipeline runs recorded` },
                    { text: `Last updated: ${lastUpdated}` },
                ]}
            />

            {/* KPI Strip */}
            <div className="summary-strip">
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--brand-primary)' }}>{tables.length}</div>
                        <div className="summary-item-label">Tables</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-info)' }}>{totalRecords.toLocaleString()}</div>
                        <div className="summary-item-label">Total Records</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-success)' }}>3</div>
                        <div className="summary-item-label">Data Layers</div>
                    </div>
                </div>
                <div style={{ width: 1, background: 'var(--border)', margin: '0 8px' }} />
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{lastUpdated}</div>
                        <div className="summary-item-label">Last Updated</div>
                    </div>
                </div>
            </div>

            {/* Architecture Overview */}
            <div className="card card-accent-top">
                <div className="section-title">
                    <span className="dot"></span>
                    Warehouse Architecture
                    <span className="section-subtitle">Data flow: Sources &rarr; Warehouse &rarr; Intelligence</span>
                </div>
                <div className="dwh-arch">
                    {/* Sources */}
                    <div className="dwh-arch-col">
                        <div className="dwh-arch-col-title">Data Sources</div>
                        <ArchNode icon={'\uD83D\uDCE1'} label="OSS Collector" sub="Network KPIs" color="info" />
                        <ArchNode icon={'\uD83D\uDCB3'} label="BSS Billing" sub="Revenue metrics" color="purple" />
                        <ArchNode icon={'\uD83D\uDCC1'} label="MinIO Storage" sub="Raw files (S3)" color="cyan" />
                    </div>

                    {/* Flow arrows */}
                    <div className="dwh-arch-arrow">
                        <svg width="40" height="24" viewBox="0 0 40 24" fill="none">
                            <path d="M4 12h28m0 0l-6-5m6 5l-6 5" stroke="var(--brand-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        <span>ETL</span>
                    </div>

                    {/* Warehouse */}
                    <div className="dwh-arch-col dwh-arch-warehouse">
                        <div className="dwh-arch-col-title">Warehouse</div>
                        <ArchNode icon={'\uD83D\uDDC4\uFE0F'} label="Raw Data" sub={`${ossData.length + bssData.length} records`} color="info" />
                        <ArchNode icon={'\u2699\uFE0F'} label="Processed" sub={`${corrData.length} correlation records`} color="purple" />
                        <ArchNode icon={'\uD83D\uDCCA'} label="Metadata" sub={`${runData.length} runs`} color="success" />
                    </div>

                    {/* Flow arrows */}
                    <div className="dwh-arch-arrow">
                        <svg width="40" height="24" viewBox="0 0 40 24" fill="none">
                            <path d="M4 12h28m0 0l-6-5m6 5l-6 5" stroke="var(--brand-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        <span>Serve</span>
                    </div>

                    {/* Use Cases */}
                    <div className="dwh-arch-col">
                        <div className="dwh-arch-col-title">Intelligence</div>
                        <ArchNode icon={'\uD83D\uDD2C'} label="Anomaly Detection" sub="VAE PyTorch" color="danger" />
                        <ArchNode icon={'\uD83D\uDCC8'} label="CEM + RAT" sub="LightGBM + XGBoost" color="warning" />
                        <ArchNode icon={'\uD83E\uDD16'} label="L4 Agent" sub="Autonomous ops" color="cyan" />
                    </div>
                </div>
            </div>

            {/* Data Catalog */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    Data Catalog
                    <span className="section-subtitle">{tables.length} tables across 3 layers</span>
                </div>
                <div className="dwh-catalog">
                    {tables.map((t) => (
                        <div key={t.id} className="dwh-catalog-item">
                            <div className="dwh-catalog-header">
                                <div className="dwh-catalog-info">
                                    <span className={`badge badge-${t.layerColor}`} style={{ fontSize: 9 }}>{t.layer}</span>
                                    <span className="dwh-catalog-name">{t.name}</span>
                                </div>
                                <div className="dwh-catalog-meta">
                                    <span className="dwh-catalog-records">{t.records.toLocaleString()} rows</span>
                                    <span className="dwh-catalog-source">{t.source}</span>
                                </div>
                            </div>
                            <div className="dwh-catalog-desc">{t.description}</div>
                            <div className="dwh-catalog-cols">
                                {t.columns.map((c) => (
                                    <span key={c} className="dwh-col-chip">{c}</span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Raw Data: OSS Anomalies */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    <span className={`badge badge-info`} style={{ fontSize: 9 }}>Raw</span>
                    oss_anomalies
                    <span className="section-subtitle">{ossData.length} records</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>cell_id</th>
                                <th>kpi_name</th>
                                <th>severity</th>
                                <th>value</th>
                                <th>baseline_value</th>
                                <th>region</th>
                                <th>created_at</th>
                            </tr>
                        </thead>
                        <tbody>
                            {ossData.slice(0, 25).map((a: any, idx: number) => (
                                <tr key={idx}>
                                    <td className="mono" style={{ color: 'var(--text-muted)', fontSize: 11 }}>{idx + 1}</td>
                                    <td className="mono">{a.cell_id ?? '\u2014'}</td>
                                    <td>{a.kpi_name ?? '\u2014'}</td>
                                    <td><ScoreBar value={a.severity ?? 0} /></td>
                                    <td className="mono">{a.value != null ? Number(a.value).toFixed(4) : '\u2014'}</td>
                                    <td className="mono" style={{ color: 'var(--text-muted)' }}>{a.baseline_value != null ? Number(a.baseline_value).toFixed(4) : '\u2014'}</td>
                                    <td>{a.region ?? '\u2014'}</td>
                                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatTs(a.created_at)}</td>
                                </tr>
                            ))}
                            {ossData.length === 0 && <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No data available</td></tr>}
                        </tbody>
                    </table>
                    {ossData.length > 25 && (
                        <div className="dwh-table-footer">Showing 25 of {ossData.length} records</div>
                    )}
                </div>
            </div>

            {/* Raw Data: BSS Revenue Anomalies */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    <span className={`badge badge-info`} style={{ fontSize: 9 }}>Raw</span>
                    cem_anomalies_table
                    <span className="section-subtitle">{bssData.length} records</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>subscriber_id</th>
                                <th>operator</th>
                                <th>line_type</th>
                                <th>plan</th>
                                <th>metric_name</th>
                                <th>severity</th>
                                <th>value</th>
                                <th>region</th>
                                <th>created_at</th>
                            </tr>
                        </thead>
                        <tbody>
                            {bssData.slice(0, 25).map((a: any, idx: number) => {
                                const sev = a.severity ?? a.score ?? 0;
                                return (
                                    <tr key={idx}>
                                        <td className="mono" style={{ color: 'var(--text-muted)', fontSize: 11 }}>{idx + 1}</td>
                                        <td className="mono" style={{ maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.subscriber_id ? a.subscriber_id.slice(0, 12) + '...' : '\u2014'}</td>
                                        <td style={{ fontWeight: 500 }}>{a.operator ?? '\u2014'}</td>
                                        <td><span className={`badge ${a.line_type === 'prepaid' ? 'badge-info' : 'badge-purple'}`}>{a.line_type ?? '\u2014'}</span></td>
                                        <td style={{ fontSize: 12 }}>{a.plan ?? '\u2014'}</td>
                                        <td style={{ fontWeight: 500 }}>{a.metric_name ?? '\u2014'}</td>
                                        <td><ScoreBar value={sev} /></td>
                                        <td className="mono">{a.value != null ? Number(a.value).toFixed(4) : '\u2014'}</td>
                                        <td>{a.region ?? '\u2014'}</td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatTs(a.created_at)}</td>
                                    </tr>
                                );
                            })}
                            {bssData.length === 0 && <tr><td colSpan={10} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No data available</td></tr>}
                        </tbody>
                    </table>
                    {bssData.length > 25 && (
                        <div className="dwh-table-footer">Showing 25 of {bssData.length} records</div>
                    )}
                </div>
            </div>

            {/* Processed: Correlations */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    <span className={`badge badge-purple`} style={{ fontSize: 9 }}>Processed</span>
                    oss_bss_correlations
                    <span className="section-subtitle">{corrData.length} records</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>metric_x</th>
                                <th>metric_y</th>
                                <th>method</th>
                                <th>corr_value</th>
                                <th>strength</th>
                                <th>p_value</th>
                                <th>significant</th>
                                <th>region</th>
                            </tr>
                        </thead>
                        <tbody>
                            {corrData.slice(0, 25).map((c: any, idx: number) => {
                                const abs = Math.abs(c.corr_value ?? 0);
                                const strength = abs >= 0.7 ? 'Strong' : abs >= 0.4 ? 'Moderate' : abs >= 0.2 ? 'Weak' : 'Negligible';
                                const strengthCls = abs >= 0.7 ? 'badge-danger' : abs >= 0.4 ? 'badge-warning' : 'badge-neutral';
                                const sig = (c.p_value ?? 1) < 0.05;
                                return (
                                    <tr key={idx}>
                                        <td className="mono" style={{ color: 'var(--text-muted)', fontSize: 11 }}>{idx + 1}</td>
                                        <td style={{ fontWeight: 500, fontSize: 12 }}>{c.metric_x ?? '\u2014'}</td>
                                        <td style={{ fontWeight: 500, fontSize: 12 }}>{c.metric_y ?? '\u2014'}</td>
                                        <td><span className="badge badge-neutral">{c.method ?? '\u2014'}</span></td>
                                        <td className="mono" style={{ fontWeight: 600, color: (c.corr_value ?? 0) > 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                                            {c.corr_value != null ? c.corr_value.toFixed(4) : '\u2014'}
                                        </td>
                                        <td><span className={`badge ${strengthCls}`}>{strength}</span></td>
                                        <td className="mono" style={{ fontSize: 12 }}>{c.p_value != null ? c.p_value.toExponential(2) : '\u2014'}</td>
                                        <td>{sig ? <span className="badge badge-success">Yes</span> : <span className="badge badge-neutral">No</span>}</td>
                                        <td>{c.region ?? '\u2014'}</td>
                                    </tr>
                                );
                            })}
                            {corrData.length === 0 && <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No data available</td></tr>}
                        </tbody>
                    </table>
                    {corrData.length > 25 && (
                        <div className="dwh-table-footer">Showing 25 of {corrData.length} records</div>
                    )}
                </div>
            </div>

            {/* Operational: Pipeline Runs */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    <span className={`badge badge-success`} style={{ fontSize: 9 }}>Operational</span>
                    pipeline_runs
                    <span className="section-subtitle">{runData.length} records</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>run_id</th>
                                <th>status</th>
                                <th>started_at</th>
                                <th>finished_at</th>
                                <th>duration</th>
                                <th>error_message</th>
                            </tr>
                        </thead>
                        <tbody>
                            {runData.slice(0, 25).map((r: any, idx: number) => {
                                const statusCls = r.status === 'succeeded' ? 'badge-success' : r.status === 'failed' ? 'badge-danger' : 'badge-warning';
                                const dur = r.started_at && r.finished_at
                                    ? ((new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()) / 1000).toFixed(1) + 's'
                                    : '\u2014';
                                return (
                                    <tr key={idx}>
                                        <td className="mono" style={{ color: 'var(--text-muted)', fontSize: 11 }}>{idx + 1}</td>
                                        <td className="mono" style={{ fontSize: 12 }}>{(r.run_id ?? r.id ?? '\u2014').toString().slice(0, 12)}</td>
                                        <td><span className={`badge ${statusCls}`}>{r.status ?? '\u2014'}</span></td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatTs(r.started_at)}</td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatTs(r.finished_at)}</td>
                                        <td className="mono">{dur}</td>
                                        <td style={{ fontSize: 12, color: 'var(--color-danger)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.error_message ?? '\u2014'}</td>
                                    </tr>
                                );
                            })}
                            {runData.length === 0 && <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No data available</td></tr>}
                        </tbody>
                    </table>
                    {runData.length > 25 && (
                        <div className="dwh-table-footer">Showing 25 of {runData.length} records</div>
                    )}
                </div>
            </div>
        </div>
    );
}
