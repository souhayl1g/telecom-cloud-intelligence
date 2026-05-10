import Link from 'next/link';
import { api } from '../../lib/api';
import PageInfoBar from '../../components/PageInfoBar';
import LeadTimeHistogram from '../../components/LeadTimeHistogram';

export const dynamic = 'force-dynamic';

function getSigColor(significant: boolean, pvalue: number) {
    if (significant) return 'var(--color-success)';
    if (pvalue < 0.1) return 'var(--color-warning)';
    return 'var(--color-danger)';
}

function getSigBg(significant: boolean, pvalue: number) {
    if (significant) return 'var(--color-success-bg)';
    if (pvalue < 0.1) return 'var(--color-warning-bg)';
    return 'var(--color-danger-bg)';
}

function getSigBorder(significant: boolean, pvalue: number) {
    if (significant) return 'var(--color-success-border)';
    if (pvalue < 0.1) return 'var(--color-warning-border)';
    return 'var(--color-danger-border)';
}

export default async function GrangerCausalityPage() {
    let data: any = null;
    try {
        data = await api.grangerCausality();
    } catch {
        /* database may be unreachable during build */
    }
    const results = (data as any)?.results ?? [];
    const summaries = (data as any)?.summaries ?? [];

    const totalPairs = summaries.length;
    const significantPairs = summaries.filter((s: any) => (s.significance_pct ?? 0) >= 50).length;
    const meanLag = summaries.length > 0
        ? summaries.reduce((sum: number, s: any) => sum + (parseFloat(s.mean_lag) || 0), 0) / summaries.length
        : 0;

    const areas = Array.from(new Set(results.map((r: any) => r.area)));

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="OSS ∩ CEM Convergence · Granger Temporal Causality"
                description="Granger causality is the statistical engine behind NeXo's OSS↔CEM convergence claim. Pearson/Spearman correlation only tells us OSS network and CEM experience move together; Granger tells us OSS network KPIs causally drive CEM subscriber experience after a measurable delay. This is the temporal-lag evidence that a CEM degradation today was caused by a network KPI shift N cycles ago — the mechanism by which the L4 ADN agent can act before users complain."
                values={[
                    { text: `${totalPairs} unique OSS→CEM pairs tested` },
                    { text: `${significantPairs} pairs with ≥50% significance` },
                    { text: `Mean optimal lag: ${meanLag.toFixed(1)} cycles` },
                ]}
            />

            {/* Detection Lead Time Panel ─────────────────────────────────── */}
            <div className="card card-accent-top">
                <div className="section-title">
                    <span className="dot" style={{ background: 'var(--color-purple, #a78bfa)' }} />
                    Detection Lead Time
                    <span className="section-subtitle">How early the model would fire vs the symptom</span>
                </div>
                <LeadTimeHistogram />
            </div>

            {/* Methodology + Convergence Explainer ─────────────────────── */}
            <div className="grid grid-2">
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot" />
                        How Granger Causality Works
                        <span className="section-subtitle">Methodology in plain terms</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>1. Hypothesis</div>
                            Past values of OSS metric <em>X</em> (say <code>cell_load_pct</code>) help predict future BSS metric <em>Y</em> (say <code>cem_score</code>) <strong>beyond</strong> what Y&apos;s own past predicts.
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>2. Two regressions</div>
                            Fit Y from its own lags (restricted model). Fit Y from its own lags + lags of X (full model). Compare residuals.
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>3. F-test</div>
                            <strong>F-statistic</strong> measures how much X&apos;s lags reduce prediction error. <strong>p-value</strong> is the probability that reduction is random noise. <code>p &lt; 0.05</code> → reject the null → X Granger-causes Y.
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>4. Optimal lag</div>
                            We test lags from 1 to N cycles and report the lag with the lowest p-value — this tells the L4 agent <em>how many cycles ahead</em> a network change manifests as a subscriber-experience change.
                        </div>
                    </div>
                </div>
                <div className="card card-accent-top">
                    <div className="section-title">
                        <span className="dot" />
                        Why This = OSS ∩ BSS Convergence
                        <span className="section-subtitle">The core thesis of NeXo</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--color-info)', marginBottom: 4 }}>OSS world</div>
                            Cell-level KPIs: throughput, latency, packet loss, RSRP, cell load. Owned by network operations.
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--color-purple)', marginBottom: 4 }}>BSS world</div>
                            Subscriber-level metrics: CEM score, churn flag, RAT gap, DOU. Owned by customer-experience teams.
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--brand-primary)', marginBottom: 4 }}>Convergence</div>
                            Without Granger, OSS and BSS are two parallel silos joined only by area aggregation. Granger proves <strong>causal direction</strong> with a measurable lag — turning two correlated streams into a single predictive signal. This is what justifies a unified CEM+OSS dashboard rather than two separate tools.
                        </div>
                        <div style={{ padding: 10, background: 'var(--color-success-bg)', border: '1px solid var(--color-success-border)', borderRadius: 8 }}>
                            <div style={{ fontWeight: 700, color: 'var(--color-success)', marginBottom: 4, fontSize: 12 }}>Reading the table below</div>
                            A row like <code>cell_load_pct → cem_score</code>, lag=3, p=0.02 means: when an area&apos;s cell load shifts, subscriber CEM score in that area changes 3 cycles later, with 98% statistical confidence. The L4 agent uses these proven pairs to act <em>before</em> the BSS effect manifests — the foundation of preemptive remediation.
                        </div>
                    </div>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-4">
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon info">{'\u2194'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Pairs Tested</div>
                            <div className="stat-value">{totalPairs}</div>
                        </div>
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon success">{'\u2713'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Significant Pairs</div>
                            <div className="stat-value" style={{ color: 'var(--color-success)' }}>{significantPairs}</div>
                        </div>
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon cyan">{'\u23F1'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Mean Optimal Lag</div>
                            <div className="stat-value">{meanLag.toFixed(1)}</div>
                            <div className="stat-sub">cycles</div>
                        </div>
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon purple">{'\u{1F4CA}'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Areas Covered</div>
                            <div className="stat-value">{areas.length}</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Summary Table */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    Causal Pair Summary
                    <span className="section-subtitle">OSS metric → BSS metric</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>OSS Metric</th>
                                <th>BSS Metric</th>
                                <th>Tests</th>
                                <th>Significant %</th>
                                <th>Mean Lag</th>
                                <th>Mean p-value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {summaries.map((s: any, idx: number) => (
                                <tr key={idx}>
                                    <td style={{ fontWeight: 500, fontSize: 12 }}>{s.oss_variable}</td>
                                    <td style={{ fontWeight: 500, fontSize: 12 }}>{s.cem_variable}</td>
                                    <td className="mono">{s.total_tests}</td>
                                    <td>
                                        <span
                                            className="badge"
                                            style={{
                                                fontSize: 10,
                                                background: (s.significance_pct ?? 0) >= 50 ? 'var(--color-success-bg)' : (s.significance_pct ?? 0) >= 20 ? 'var(--color-warning-bg)' : 'var(--color-danger-bg)',
                                                color: (s.significance_pct ?? 0) >= 50 ? 'var(--color-success)' : (s.significance_pct ?? 0) >= 20 ? 'var(--color-warning)' : 'var(--color-danger)',
                                                border: `1px solid ${(s.significance_pct ?? 0) >= 50 ? 'var(--color-success-border)' : (s.significance_pct ?? 0) >= 20 ? 'var(--color-warning-border)' : 'var(--color-danger-border)'}`,
                                            }}
                                        >
                                            {s.significance_pct}%
                                        </span>
                                    </td>
                                    <td className="mono">{s.mean_lag}</td>
                                    <td className="mono" style={{ fontSize: 12 }}>{parseFloat(s.mean_pvalue).toExponential(2)}</td>
                                </tr>
                            ))}
                            {summaries.length === 0 && (
                                <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No Granger causality data available</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Area × Pair Heatmap */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    Area × Causal Pair Heatmap
                    <span className="section-subtitle">Color-coded by significance</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Area</th>
                                <th>OSS → BSS</th>
                                <th>Lag</th>
                                <th>p-value</th>
                                <th>F-stat</th>
                                <th>Significant</th>
                            </tr>
                        </thead>
                        <tbody>
                            {results.slice(0, 100).map((r: any, idx: number) => (
                                <tr key={idx}>
                                    <td style={{ fontWeight: 500, fontSize: 12 }}>{r.area}</td>
                                    <td style={{ fontSize: 12 }}>
                                        <span style={{ color: 'var(--color-info)' }}>{r.oss_variable}</span>
                                        {' \u2192 '}
                                        <span style={{ color: 'var(--color-purple)' }}>{r.cem_variable}</span>
                                    </td>
                                    <td className="mono">{r.best_lag ?? '\u2014'}</td>
                                    <td className="mono" style={{ fontSize: 12 }}>
                                        {r.best_pvalue != null ? r.best_pvalue.toExponential(2) : '\u2014'}
                                    </td>
                                    <td className="mono" style={{ fontSize: 12 }}>
                                        {r.best_fstat != null ? r.best_fstat.toFixed(2) : '\u2014'}
                                    </td>
                                    <td>
                                        <span
                                            className="badge"
                                            style={{
                                                fontSize: 10,
                                                background: getSigBg(r.significant, r.best_pvalue ?? 1),
                                                color: getSigColor(r.significant, r.best_pvalue ?? 1),
                                                border: `1px solid ${getSigBorder(r.significant, r.best_pvalue ?? 1)}`,
                                            }}
                                        >
                                            {r.significant ? 'YES' : 'NO'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                            {results.length === 0 && (
                                <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No Granger causality data available</td></tr>
                            )}
                        </tbody>
                    </table>
                    {results.length > 100 && (
                        <div className="dwh-table-footer">Showing 100 of {results.length} records</div>
                    )}
                </div>
            </div>
        </div>
    );
}
