import { api } from '../../lib/api';
import RootCauseAnalysis from '../../components/RootCauseAnalysis';
import AnomalyTimeline from '../../components/AnomalyTimeline';
import PageInfoBar from '../../components/PageInfoBar';

export const dynamic = 'force-dynamic';

export default async function IntelligencePage() {
    const [oss, bss, corrs, cemSummary] = await Promise.all([
        api.anomalies(),
        api.cemAnomalies(),
        api.correlation(),
        api.cemScores(),
    ]);

    const ossData = oss ?? [];
    const bssData = bss ?? [];
    const corrData = corrs ?? [];
    const cemAvg = (cemSummary as any)?.avg_score ?? 0;

    const totalAnomalies = ossData.length + bssData.length;
    const criticalCount = ossData.filter((a: any) => a.severity > 0.9).length + bssData.filter((a: any) => (a.severity ?? a.score ?? 0) > 0.8).length;
    const strongCorrs = corrData.filter((c: any) => Math.abs(c.corr_value) >= 0.7).length;

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Synthesis · Cross-Domain Intelligence"
                description="Why did this happen? Three signals — OSS anomalies, CEM anomalies, OSS↔CEM correlations — are fused into a single causal narrative. Instead of reading multiple dashboards, you read one root-cause story with the evidence attached."
                values={[
                    { text: `${totalAnomalies} anomalies · ${criticalCount} critical` },
                    { text: `CEM avg: ${(cemAvg * 100).toFixed(1)}%` },
                    { text: `${strongCorrs} strong cross-domain correlations feeding the narrative` },
                ]}
            />

            {/* Quick stats */}
            <div className="summary-strip">
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--brand-primary)' }}>{totalAnomalies}</div>
                        <div className="summary-item-label">Total Anomalies</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-danger)' }}>{criticalCount}</div>
                        <div className="summary-item-label">Critical</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-warning)' }}>{(cemAvg * 100).toFixed(1)}%</div>
                        <div className="summary-item-label">CEM Score</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-cyan)' }}>{strongCorrs}</div>
                        <div className="summary-item-label">Strong Correlations</div>
                    </div>
                </div>
            </div>

            {/* AI Root Cause Analysis */}
            <div className="card card-accent-top">
                <div className="section-title">
                    <span className="dot"></span>
                    AI Root Cause Analysis
                    <span className="section-subtitle">Automated cross-domain intelligence</span>
                </div>
                <RootCauseAnalysis
                    sla={{ score: 0 }}
                    ossAnomalies={ossData}
                    cemAnomalies={bssData}
                    correlations={corrData}
                />
            </div>

            {/* Real-time Anomaly Timeline */}
            <div className="card card-accent-top">
                <div className="section-title">
                    <span className="dot"></span>
                    Anomaly Event Stream
                    <span className="section-subtitle">{totalAnomalies} events &middot; OSS + CEM</span>
                </div>
                <AnomalyTimeline
                    ossAnomalies={ossData}
                    cemAnomalies={bssData}
                />
            </div>
        </div>
    );
}
