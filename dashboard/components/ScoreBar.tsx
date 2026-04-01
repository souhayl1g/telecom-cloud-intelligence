"use client";

export default function ScoreBar({ value, max = 1 }: { value: number; max?: number }) {
    const pct = Math.min((value / max) * 100, 100);
    let color = 'var(--color-success)';
    if (pct >= 70) color = 'var(--color-danger)';
    else if (pct >= 40) color = 'var(--color-warning)';

    return (
        <div className="score-bar">
            <span className="score-bar-value" style={{ color }}>{value.toFixed(3)}</span>
            <div className="score-bar-track">
                <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
            </div>
        </div>
    );
}
