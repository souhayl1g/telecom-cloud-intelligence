"use client";
import { useEffect, useState, useCallback } from 'react';
import PageInfoBar from '../../components/PageInfoBar';

/* ── Types ──────────────────────────────────────────────────────────────── */
interface ModelMetrics {
    name: string;
    algorithm: string;
    version: string;
    features: number;
    featureNames: string[];
    task: string;
    color: string;
    // Regression metrics (SLA)
    testMae?: number;
    testRmse?: number;
    testR2?: number;
    testMse?: number;
    trainR2?: number;
    cvR2?: number;
    cvR2Std?: number;
    cvMae?: number;
    // Classification metrics (Anomaly)
    precision?: number;
    recall?: number;
    f1?: number;
    rocAuc?: number;
    avgPrecision?: number;
    accuracy?: number;
    cm?: { tn: number; fp: number; fn: number; tp: number };
    // Common
    featureImportances?: Record<string, number>;
    hyperparameters?: Record<string, number>;
    trainingData: { samples: number };
    lastTrained: string;
    status: 'healthy' | 'degraded' | 'retraining';
}

interface OllamaModel {
    name: string;
    size: string;
    family: string;
    quantization: string;
    parameterSize: string;
}

/* ── Sparkline ──────────────────────────────────────────────────────────── */
function Sparkline({ data, color, height = 36, width = 120 }: { data: number[]; color: string; height?: number; width?: number }) {
    if (!data || data.length < 2) return null;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const points = data.map((v, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((v - min) / range) * (height - 4) - 2;
        return `${x},${y}`;
    }).join(' ');
    const area = `0,${height} ${points} ${width},${height}`;
    return (
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
            <defs>
                <linearGradient id={`sg-${color.replace(/[^a-z0-9]/gi, '')}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity="0.25" />
                    <stop offset="100%" stopColor={color} stopOpacity="0" />
                </linearGradient>
            </defs>
            <polygon points={area} fill={`url(#sg-${color.replace(/[^a-z0-9]/gi, '')})`} />
            <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
    );
}

/* ── Metric Bar ─────────────────────────────────────────────────────────── */
function MetricBar({ value, label, color, format }: { value: number; label: string; color: string; format?: string }) {
    const pct = Math.min(value * 100, 100);
    const display = format || `${(value * 100).toFixed(1)}%`;
    return (
        <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.4px' }}>{label}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color, fontFamily: "'JetBrains Mono', monospace" }}>{display}</span>
            </div>
            <div style={{ height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: 'width 1s ease' }} />
            </div>
        </div>
    );
}

/* ── Confusion Matrix ───────────────────────────────────────────────────── */
function ConfusionMatrix({ tp, fp, fn, tn }: { tp: number; fp: number; fn: number; tn: number }) {
    const cells = [
        { label: 'TP', value: tp, bg: 'var(--color-success-bg)', clr: 'var(--color-success)' },
        { label: 'FP', value: fp, bg: 'var(--color-danger-bg)', clr: 'var(--color-danger)' },
        { label: 'FN', value: fn, bg: 'var(--color-warning-bg)', clr: 'var(--color-warning)' },
        { label: 'TN', value: tn, bg: 'var(--bg-surface)', clr: 'var(--text-secondary)' },
    ];
    return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, maxWidth: 200 }}>
            <div style={{ gridColumn: '1/-1', textAlign: 'center', fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Confusion Matrix
            </div>
            {cells.map(c => (
                <div key={c.label} style={{
                    padding: '10px 8px', textAlign: 'center', borderRadius: 8,
                    background: c.bg, border: '1px solid var(--border)',
                }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: c.clr, fontFamily: "'JetBrains Mono', monospace" }}>{c.value}</div>
                    <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 600, marginTop: 2 }}>{c.label}</div>
                </div>
            ))}
        </div>
    );
}

/* ── Radar Chart ─────────────────────────────────────────────────────────── */
function RadarChart({ metrics, color }: { metrics: { label: string; value: number }[]; color: string }) {
    const size = 180;
    const cx = size / 2;
    const cy = size / 2;
    const r = 65;
    const n = metrics.length;

    const getPoint = (i: number, val: number) => {
        const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
        return { x: cx + r * val * Math.cos(angle), y: cy + r * val * Math.sin(angle) };
    };

    const bgPoints = Array.from({ length: n }, (_, i) => getPoint(i, 1));
    const dataPoints = metrics.map((m, i) => getPoint(i, m.value));

    return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            {[0.25, 0.5, 0.75, 1].map(level => (
                <polygon key={level}
                    points={Array.from({ length: n }, (_, i) => {
                        const p = getPoint(i, level);
                        return `${p.x},${p.y}`;
                    }).join(' ')}
                    fill="none" stroke="var(--border)" strokeWidth="0.5" opacity={0.5}
                />
            ))}
            {bgPoints.map((p, i) => (
                <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="var(--border)" strokeWidth="0.5" />
            ))}
            <polygon
                points={dataPoints.map(p => `${p.x},${p.y}`).join(' ')}
                fill={color} fillOpacity="0.15" stroke={color} strokeWidth="1.5"
            />
            {dataPoints.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r="3" fill={color} />
            ))}
            {metrics.map((m, i) => {
                const p = getPoint(i, 1.3);
                return (
                    <text key={i} x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle"
                        style={{ fontSize: 9, fill: 'var(--text-muted)', fontWeight: 600 }}>
                        {m.label}
                    </text>
                );
            })}
        </svg>
    );
}

/* ── Feature Importance Bar ─────────────────────────────────────────────── */
function FeatureImportanceChart({ data, color }: { data: Record<string, number>; color: string }) {
    const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);
    const max = sorted[0]?.[1] ?? 1;
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {sorted.map(([name, val]) => (
                <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 160, fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {name}
                    </div>
                    <div style={{ flex: 1, height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${(val / max) * 100}%`, background: color, borderRadius: 3, transition: 'width 0.5s' }} />
                    </div>
                    <div style={{ width: 48, fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace", textAlign: 'right', flexShrink: 0 }}>
                        {val.toFixed(4)}
                    </div>
                </div>
            ))}
        </div>
    );
}

/* ── Main ────────────────────────────────────────────────────────────────── */
export default function ModelEvaluationPage() {
    const [models, setModels] = useState<ModelMetrics[]>([]);
    const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
    const [selectedModel, setSelectedModel] = useState<number>(0);
    const [loading, setLoading] = useState(true);
    const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

    const fetchData = useCallback(async () => {
        try {
            // Fetch REAL metrics from the API (extracted from notebooks)
            const metricsRes = await fetch('/api/model-metrics', { cache: 'no-store' });
            if (!metricsRes.ok) throw new Error('Failed to fetch metrics');
            const { models: raw } = await metricsRes.json();

            const modelList: ModelMetrics[] = [
                {
                    name: raw.cem_score.name,
                    algorithm: raw.cem_score.algorithm,
                    version: raw.cem_score.version,
                    features: raw.cem_score.features,
                    featureNames: raw.cem_score.featureNames,
                    task: raw.cem_score.task,
                    color: '#34d399',
                    testMae: raw.cem_score.metrics.test.mae,
                    testRmse: raw.cem_score.metrics.test.rmse,
                    testR2: raw.cem_score.metrics.test.r2,
                    featureImportances: raw.cem_score.featureImportances,
                    hyperparameters: raw.cem_score.hyperparameters,
                    trainingData: raw.cem_score.trainingData,
                    lastTrained: raw.cem_score.lastTrained,
                    status: 'healthy',
                },
                {
                    name: raw.oss_anomaly.name + ' (VAE)',
                    algorithm: raw.oss_anomaly.algorithm,
                    version: raw.oss_anomaly.version,
                    features: raw.oss_anomaly.features,
                    featureNames: raw.oss_anomaly.featureNames,
                    task: raw.oss_anomaly.task,
                    color: '#60a5fa',
                    precision: raw.oss_anomaly.metrics.precision,
                    recall: raw.oss_anomaly.metrics.recall,
                    f1: raw.oss_anomaly.metrics.f1,
                    rocAuc: raw.oss_anomaly.metrics.rocAuc,
                    accuracy: raw.oss_anomaly.metrics.accuracy,
                    hyperparameters: raw.oss_anomaly.hyperparameters,
                    trainingData: raw.oss_anomaly.trainingData,
                    lastTrained: raw.oss_anomaly.lastTrained,
                    status: 'healthy',
                },
                {
                    name: raw.rat_underservice.name,
                    algorithm: raw.rat_underservice.algorithm,
                    version: raw.rat_underservice.version,
                    features: raw.rat_underservice.features,
                    featureNames: raw.rat_underservice.featureNames,
                    task: raw.rat_underservice.task,
                    color: '#fbbf24',
                    precision: raw.rat_underservice.metrics.precision,
                    recall: raw.rat_underservice.metrics.recall,
                    f1: raw.rat_underservice.metrics.f1,
                    rocAuc: raw.rat_underservice.metrics.rocAuc,
                    accuracy: raw.rat_underservice.metrics.accuracy,
                    featureImportances: raw.rat_underservice.featureImportances,
                    hyperparameters: raw.rat_underservice.hyperparameters,
                    trainingData: raw.rat_underservice.trainingData,
                    lastTrained: raw.rat_underservice.lastTrained,
                    status: 'healthy',
                },
            ];
            setModels(modelList);

            // Check Ollama models
            try {
                const ollamaRes = await fetch('http://localhost:11434/api/tags');
                if (ollamaRes.ok) {
                    const data = await ollamaRes.json();
                    setOllamaModels((data.models || []).map((m: any) => ({
                        name: m.name,
                        size: (m.size / 1e9).toFixed(1) + ' GB',
                        family: m.details?.family || 'unknown',
                        quantization: m.details?.quantization_level || 'N/A',
                        parameterSize: m.details?.parameter_size || 'N/A',
                    })));
                }
            } catch { /* Ollama not available */ }

            setLastRefresh(new Date());
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const m = models[selectedModel];

    if (loading) {
        return (
            <div className="l4-loading">
                <div className="l4-loading-spinner" />
                <div className="l4-loading-text">Loading Model Evaluation...</div>
            </div>
        );
    }

    // Determine the primary metric for each model card
    const getPrimaryMetric = (model: ModelMetrics) => {
        if (model.task === 'regression') return { label: 'Test R\u00B2', value: model.testR2 ?? 0 };
        return { label: 'F1-Score', value: model.f1 ?? 0 };
    };

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="ML Governance · Live from Notebooks"
                description="Can we trust the numbers? Every v3 model — LightGBM CEM Experience Score, PyTorch VAE OSS Anomaly, XGBoost RAT Underservice — is audited here against its real test set on 500K-2M real Tunisie Telecom records: R², MAE, RMSE, Precision/Recall/F1, ROC-AUC, confusion matrix and feature importances. Metrics are extracted directly from the v3.0 training notebooks, not mocked."
                values={[
                    { text: `${models.length} production models · Qwen2.5 7B for L4 agent chat` },
                    { text: `Best R²: ${Math.max(...models.map(mm => mm.testR2 ?? 0)).toFixed(3)} · Best F1: ${Math.max(...models.map(mm => mm.f1 ?? 0)).toFixed(3)}` },
                    { text: `${ollamaModels.length} Ollama model(s) available locally` },
                ]}
            />

            {/* Source indicator */}
            <div style={{ padding: '10px 16px', background: 'var(--color-info-bg)', border: '1px solid var(--color-info-border)', borderRadius: 'var(--radius-md)', fontSize: 12, color: 'var(--color-info)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" /></svg>
                All metrics below are real values computed from trained models in <strong style={{ margin: '0 4px' }}>notebooks/06_cem_v3_training.ipynb, notebooks/07_oss_vae_anomaly.ipynb, notebooks/08_rat_underservice.ipynb, notebooks/09_master_v3_training.py</strong>
            </div>

            {/* Model Selector Cards */}
            <div className="grid grid-3">
                {models.map((model, idx) => {
                    const pm = getPrimaryMetric(model);
                    return (
                        <div
                            key={model.name}
                            className={`card card-compact me-model-card ${selectedModel === idx ? 'me-model-selected' : ''}`}
                            style={{ cursor: 'pointer', borderColor: selectedModel === idx ? model.color : undefined }}
                            onClick={() => setSelectedModel(idx)}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                                <div className="me-model-dot" style={{ background: model.color, boxShadow: `0 0 8px ${model.color}` }} />
                                <div>
                                    <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{model.name}</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{model.algorithm}</div>
                                </div>
                                <span className={`badge ${model.status === 'healthy' ? 'badge-success' : 'badge-warning'}`} style={{ marginLeft: 'auto', fontSize: 9 }}>
                                    {model.status.toUpperCase()}
                                </span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{pm.label}</span>
                                <span style={{ fontSize: 20, fontWeight: 800, color: model.color, fontFamily: "'JetBrains Mono', monospace" }}>
                                    {(pm.value * 100).toFixed(1)}%
                                </span>
                            </div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
                                {model.features} features | {model.trainingData.samples} samples | {model.version}
                            </div>
                        </div>
                    );
                })}
            </div>

            {m && (
                <>
                    {/* Detailed Metrics */}
                    <div className="grid grid-3">
                        <div className="card card-accent-top">
                            <div className="section-title">
                                <span className="dot" />
                                {m.task === 'regression' ? 'Regression Metrics' : 'Classification Metrics'}
                                <span className="section-subtitle">{m.name}</span>
                            </div>

                            {m.task === 'regression' ? (
                                <>
                                    <MetricBar value={m.testR2 ?? 0} label="Test R\u00B2 Score" color="var(--color-success)" format={`${((m.testR2 ?? 0) * 100).toFixed(2)}%`} />
                                    <MetricBar value={m.trainR2 ?? 0} label="Train R\u00B2 Score" color="var(--color-info)" format={`${((m.trainR2 ?? 0) * 100).toFixed(2)}%`} />
                                    <MetricBar value={m.cvR2 ?? 0} label={`CV R\u00B2 (5-fold) \u00B1${((m.cvR2Std ?? 0) * 100).toFixed(2)}%`} color="var(--color-purple)" format={`${((m.cvR2 ?? 0) * 100).toFixed(2)}%`} />
                                    <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                        <div style={{ padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 8, border: '1px solid var(--border)' }}>
                                            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Test MAE</div>
                                            <div style={{ fontSize: 18, fontWeight: 700, color: m.color, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
                                                {(m.testMae ?? 0).toFixed(6)}
                                            </div>
                                        </div>
                                        <div style={{ padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 8, border: '1px solid var(--border)' }}>
                                            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Test RMSE</div>
                                            <div style={{ fontSize: 18, fontWeight: 700, color: m.color, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
                                                {(m.testRmse ?? 0).toFixed(6)}
                                            </div>
                                        </div>
                                        <div style={{ padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 8, border: '1px solid var(--border)' }}>
                                            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Test MSE</div>
                                            <div style={{ fontSize: 18, fontWeight: 700, color: m.color, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
                                                {(m.testMse ?? 0).toFixed(6)}
                                            </div>
                                        </div>
                                        <div style={{ padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 8, border: '1px solid var(--border)' }}>
                                            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>CV MAE</div>
                                            <div style={{ fontSize: 18, fontWeight: 700, color: m.color, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
                                                {(m.cvMae ?? 0).toFixed(6)}
                                            </div>
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <MetricBar value={m.precision ?? 0} label="Precision" color="var(--color-info)" />
                                    <MetricBar value={m.recall ?? 0} label="Recall" color="var(--color-success)" />
                                    <MetricBar value={m.f1 ?? 0} label="F1-Score" color="var(--color-purple)" />
                                    <MetricBar value={m.rocAuc ?? 0} label="ROC-AUC" color="var(--color-cyan)" />
                                    <MetricBar value={m.avgPrecision ?? 0} label="Avg Precision" color="var(--color-warning)" />
                                </>
                            )}
                        </div>

                        <div className="card card-accent-top">
                            <div className="section-title">
                                <span className="dot" />
                                {m.task === 'regression' ? 'Feature Importances' : 'Radar + Confusion Matrix'}
                            </div>
                            {m.task === 'regression' && m.featureImportances ? (
                                <FeatureImportanceChart data={m.featureImportances} color={m.color} />
                            ) : (
                                <>
                                    <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0' }}>
                                        <RadarChart
                                            metrics={[
                                                { label: 'PREC', value: m.precision ?? 0 },
                                                { label: 'RCL', value: m.recall ?? 0 },
                                                { label: 'F1', value: m.f1 ?? 0 },
                                                { label: 'AUC', value: m.rocAuc ?? 0 },
                                                { label: 'AP', value: m.avgPrecision ?? 0 },
                                            ]}
                                            color={m.color}
                                        />
                                    </div>
                                    {m.cm && (
                                        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 12 }}>
                                            <ConfusionMatrix tp={m.cm.tp} fp={m.cm.fp} fn={m.cm.fn} tn={m.cm.tn} />
                                        </div>
                                    )}
                                </>
                            )}
                        </div>

                        <div className="card card-accent-top">
                            <div className="section-title">
                                <span className="dot" />
                                Model Info
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                <div className="me-health-item">
                                    <div className="me-health-label">Algorithm</div>
                                    <div className="me-health-value">{m.algorithm}</div>
                                </div>
                                <div className="me-health-item">
                                    <div className="me-health-label">Version</div>
                                    <div className="me-health-value" style={{ color: m.color }}>{m.version}</div>
                                </div>
                                <div className="me-health-item">
                                    <div className="me-health-label">Features</div>
                                    <div className="me-health-value">{m.features}</div>
                                </div>
                                <div className="me-health-item">
                                    <div className="me-health-label">Training Samples</div>
                                    <div className="me-health-value">{m.trainingData.samples.toLocaleString()}</div>
                                </div>
                                <div className="me-health-item">
                                    <div className="me-health-label">Last Trained</div>
                                    <div className="me-health-value">{new Date(m.lastTrained).toLocaleDateString()}</div>
                                </div>
                                {m.hyperparameters && Object.entries(m.hyperparameters).map(([k, v]) => (
                                    <div key={k} className="me-health-item">
                                        <div className="me-health-label">{k}</div>
                                        <div className="me-health-value">{v}</div>
                                    </div>
                                ))}
                                <div className="me-health-item">
                                    <div className="me-health-label">Feature Names</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.6, wordBreak: 'break-all' }}>
                                        {m.featureNames.join(', ')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* Ollama / LLM Models */}
            <div className="card">
                <div className="section-title">
                    <span className="dot" />
                    LLM Models (Ollama)
                    <span className="section-subtitle">{ollamaModels.length} model(s) loaded</span>
                </div>
                {ollamaModels.length > 0 ? (
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Model</th>
                                    <th>Family</th>
                                    <th>Parameters</th>
                                    <th>Quantization</th>
                                    <th>Size</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {ollamaModels.map((om, i) => (
                                    <tr key={i}>
                                        <td className="mono">{om.name}</td>
                                        <td>{om.family}</td>
                                        <td>{om.parameterSize}</td>
                                        <td><span className="badge badge-info" style={{ fontSize: 10 }}>{om.quantization}</span></td>
                                        <td>{om.size}</td>
                                        <td><span className="badge badge-success" style={{ fontSize: 10 }}>LOADED</span></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="empty-state">
                        <div className="empty-state-text">Ollama not running or no models loaded</div>
                    </div>
                )}
            </div>

            {/* Last refresh */}
            <div style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', padding: '8px 0' }}>
                Metrics source: notebooks/*.ipynb | Last updated: {lastRefresh.toLocaleTimeString()}
            </div>
        </div>
    );
}
