"use client";

function getRiskLevel(score: number): { label: string; color: string; bg: string; border: string } {
    if (score >= 0.7) return { label: 'CRITICAL', color: 'var(--color-danger)', bg: 'var(--color-danger-bg)', border: 'var(--color-danger-border)' };
    if (score >= 0.4) return { label: 'WARNING', color: 'var(--color-warning)', bg: 'var(--color-warning-bg)', border: 'var(--color-warning-border)' };
    return { label: 'HEALTHY', color: 'var(--color-success)', bg: 'var(--color-success-bg)', border: 'var(--color-success-border)' };
}

export default function RiskGauge({ score, region, modelVersion }: { score: number; region?: string; modelVersion?: string }) {
    const risk = getRiskLevel(score);
    const pct = Math.round(score * 100);

    return (
        <div className="gauge-container">
            <div className="gauge-value" style={{ color: risk.color }}>{score.toFixed(3)}</div>
            <div className="gauge-label" style={{ background: risk.bg, color: risk.color, border: `1px solid ${risk.border}` }}>
                {risk.label}
            </div>
            <div className="gauge-bar">
                <div
                    className="gauge-bar-fill"
                    style={{
                        width: `${pct}%`,
                        background: `linear-gradient(90deg, var(--color-success), var(--color-warning) 50%, var(--color-danger))`,
                    }}
                />
            </div>
            <div className="gauge-zones">
                <span>0.0 Safe</span>
                <span>0.4 Warning</span>
                <span>0.7 Critical</span>
                <span>1.0</span>
            </div>
            {(region || modelVersion) && (
                <div style={{ marginTop: 14, display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-muted)' }}>
                    {region && <span>Region: <strong style={{ color: 'var(--text-secondary)' }}>{region}</strong></span>}
                    {modelVersion && <span>Model: <strong style={{ color: 'var(--text-secondary)' }}>{modelVersion}</strong></span>}
                </div>
            )}
        </div>
    );
}
