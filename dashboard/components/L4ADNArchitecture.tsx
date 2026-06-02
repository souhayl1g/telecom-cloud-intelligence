"use client";
import { useState } from 'react';

interface ADNArchitectureProps {
    cemAvg: number;
    vaeAnomalies: number;
    ratRate: number;
    grangerSig: number;
    correlationsCount: number;
    pendingActions: number;
    autoApprovedCount: number;
    cycleLatencyMs: number;
}

/* ── ADN L4 Architecture Hero ────────────────────────────────────────────────
 *
 * Mirrors Huawei's ADN Level 4 industry blueprint (TM Forum, June 2024):
 *   • 3-layer architecture: Business Ops / Service Ops / Resource Ops
 *   • 4-step closed loop: Awareness → Analysis → Decision → Execution
 *   • Mate copilots (role-based) + Spirit agents (scenario-specific)
 *
 * NeXo's project-specific touch:
 *   • Tunisie Telecom area names (TATAOUINE, SFX*, ZGT*, MAHDIA, GABES, …)
 *   • OSS ∩ CEM convergence as the central thesis (driven by Granger causality)
 *   • Real ML models in the Decision layer (LightGBM CEM, PyTorch VAE, XGBoost RAT)
 * ───────────────────────────────────────────────────────────────────────── */

export default function L4ADNArchitecture({
    cemAvg, vaeAnomalies, ratRate, grangerSig,
    correlationsCount, pendingActions, autoApprovedCount, cycleLatencyMs,
}: ADNArchitectureProps) {
    const [cardOpen, setCardOpen] = useState(false);

    // Autonomy level — score the system's current closed-loop performance
    const autonomyScore = Math.min(100,
        (autoApprovedCount > 0 ? 25 : 0) +              // execution autonomy
        (cycleLatencyMs < 500 ? 25 : cycleLatencyMs < 2000 ? 15 : 5) +  // analysis speed
        (grangerSig >= 5 ? 25 : grangerSig >= 1 ? 15 : 5) +              // causal awareness
        (pendingActions === 0 ? 25 : pendingActions < 5 ? 15 : 5)        // decision quality
    );
    const autonomyLevel = autonomyScore >= 80 ? 'L4' : autonomyScore >= 60 ? 'L3' : autonomyScore >= 40 ? 'L2' : 'L1';

    return (
        <div className="card card-accent-top" style={{ padding: 0, overflow: 'hidden' }}>
            {/* ── Header bar ────────────────────────────────────────────── */}
            <div style={{
                padding: '18px 24px',
                background: 'linear-gradient(135deg, rgba(199,0,11,0.08) 0%, rgba(240,138,36,0.05) 100%)',
                borderBottom: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
            }}>
                <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1.4, fontWeight: 600 }}>
                        Live Autonomy Status · Tunisie Telecom
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                        Operations Control
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '8px 16px', background: 'var(--bg-elevated)', borderRadius: 12, border: '1px solid var(--border)' }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Autonomy</div>
                            <div style={{ fontSize: 24, fontWeight: 800, color: '#ffd700', fontFamily: "'Fira Code', monospace" }}>{autonomyLevel}</div>
                        </div>
                        <div style={{ width: 1, height: 30, background: 'var(--border)' }} />
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Score</div>
                            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>{autonomyScore}/100</div>
                        </div>
                    </div>
                    <button
                        onClick={() => setCardOpen(!cardOpen)}
                        title={cardOpen ? 'Collapse architecture' : 'Expand architecture'}
                        style={{
                            background: 'var(--bg-elevated)',
                            border: '1px solid var(--border)',
                            borderRadius: 8,
                            padding: '8px 10px',
                            cursor: 'pointer',
                            color: 'var(--text-muted)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.2s',
                        }}
                        onMouseEnter={(e) => {
                            (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--brand-primary)';
                            (e.currentTarget as HTMLButtonElement).style.color = 'var(--brand-primary)';
                        }}
                        onMouseLeave={(e) => {
                            (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
                            (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)';
                        }}
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                            style={{ transform: cardOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </button>
                </div>
            </div>

            {cardOpen && (
                <div style={{ maxHeight: '55vh', overflowY: 'auto' }}>
                    {/* ── 3-layer architecture ────────────────────────────────── */}
                    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>

                        {/* Business Operations layer */}
                        <ADNLayer
                            name="Business Operations"
                            sub="Service marketing, monetization, customer experience"
                            color="var(--brand-primary)"
                            items={[
                                { label: 'CEM Avg', value: cemAvg.toFixed(3), tone: cemAvg >= 0.6 ? 'good' : cemAvg >= 0.3 ? 'warn' : 'bad' },
                                { label: 'CEM Poor %', value: `${((1 - (cemAvg < 0.3 ? 0 : 1)) * 100).toFixed(0)}%` },
                                { label: 'Active Spirits', value: '5' },
                            ]}
                        />

                        {/* Service Operations layer */}
                        <ADNLayer
                            name="Service Operations"
                            sub="Spirit agents (scenario-specific autonomy) + Mate copilots (role-based)"
                            color="var(--color-purple)"
                            items={[
                                { label: 'Granger Pairs', value: String(grangerSig), tone: grangerSig >= 5 ? 'good' : 'warn' },
                                { label: 'Correlations', value: String(correlationsCount) },
                                { label: 'Pending', value: String(pendingActions), tone: pendingActions > 5 ? 'warn' : 'good' },
                            ]}
                        />

                        {/* Resource Operations layer */}
                        <ADNLayer
                            name="Resource Operations"
                            sub="OSS network resources + CEM subscriber data + ML inference"
                            color="var(--color-info)"
                            items={[
                                { label: 'VAE Anomalies', value: vaeAnomalies.toLocaleString(), tone: vaeAnomalies > 50000 ? 'warn' : 'good' },
                                { label: 'RAT Underservice', value: `${ratRate.toFixed(1)}%`, tone: ratRate > 20 ? 'bad' : ratRate > 10 ? 'warn' : 'good' },
                                { label: 'Cycle Latency', value: `${cycleLatencyMs}ms`, tone: cycleLatencyMs < 500 ? 'good' : 'warn' },
                            ]}
                        />
                    </div>

                    {/* ── Closed-loop progress ─────────────────────────────────── */}
                    <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)', background: 'rgba(255,255,255,0.02)' }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1.2, fontWeight: 600, marginBottom: 12 }}>
                            Closed-Loop Cycle (every 30s)
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                            <ClosedLoopStep n={1} label="Awareness" detail="OSS+CEM telemetry pull, mat-view refresh" tone="good" />
                            <Arrow />
                            <ClosedLoopStep n={2} label="Analysis" detail={`${grangerSig} causal pairs · 3 ML models scoring`} tone="good" />
                            <Arrow />
                            <ClosedLoopStep n={3} label="Decision" detail={`${pendingActions} pending · ${autoApprovedCount} auto-approved`} tone={pendingActions > 0 ? 'warn' : 'good'} />
                            <Arrow />
                            <ClosedLoopStep n={4} label="Execution" detail="Real playbooks → backend services" tone="good" />
                        </div>
                    </div>

                    {/* ── Spirits + Mates roster ────────────────────────────────── */}
                    <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                        <div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1.2, fontWeight: 600, marginBottom: 10 }}>
                                Spirit Agents · Scenario-Specific Autonomy
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                <RosterRow icon="favorite" name="ExperienceSpirit" scope="CEM scoring · LightGBM DART · 2.47M subs" />
                                <RosterRow icon="cell_tower" name="NetworkSpirit" scope="VAE anomaly · PyTorch · 19.3M cell records" />
                                <RosterRow icon="signal_cellular_alt" name="UnderserviceSpirit" scope="RAT gap · XGBoost GPU · per-subscriber" />
                                <RosterRow icon="hub" name="ConvergenceSpirit" scope="OSS ∩ CEM Granger causality · L4 backbone" />
                                <RosterRow icon="bolt" name="ActionSpirit" scope="Playbook execution · auto-approve guardrails" />
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1.2, fontWeight: 600, marginBottom: 10 }}>
                                Mate Copilots · Role-Based Assistants
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                <RosterRow icon="support_agent" name="NOCMate" scope="Live monitoring + intent-to-action chat" />
                                <RosterRow icon="insights" name="AnalystMate" scope="Cross-domain root-cause synthesis (intelligence page)" />
                                <RosterRow icon="engineering" name="FieldMate" scope="Playbook explainability for field engineers" />
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function ADNLayer({ name, sub, color, items, defaultOpen = true }: {
    name: string; sub: string; color: string;
    items: { label: string; value: string; tone?: 'good' | 'warn' | 'bad' }[];
    defaultOpen?: boolean;
}) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div style={{
            display: 'flex', flexDirection: 'column',
            background: 'var(--bg-elevated)',
            border: `1px solid var(--border)`,
            borderLeft: `3px solid ${color}`,
            borderRadius: 8,
            overflow: 'hidden',
        }}>
            <div
                onClick={() => setOpen(!open)}
                style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 16px',
                    cursor: 'pointer',
                    gap: 16,
                    flexWrap: 'wrap',
                }}
            >
                <div style={{ minWidth: 200 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>
                </div>
                <svg
                    width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                    style={{
                        transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s ease',
                        color: 'var(--text-muted)',
                        flexShrink: 0,
                    }}
                >
                    <polyline points="6 9 12 15 18 9" />
                </svg>
            </div>
            {open && (
                <div style={{
                    display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end',
                    padding: '0 16px 12px 16px',
                }}>
                    {items.map((it, i) => (
                        <div key={i} style={{
                            padding: '6px 12px',
                            background: 'var(--bg-surface)',
                            border: '1px solid var(--border)',
                            borderRadius: 6,
                            minWidth: 110,
                        }}>
                            <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.6, fontWeight: 600 }}>
                                {it.label}
                            </div>
                            <div style={{
                                fontSize: 14, fontWeight: 700, marginTop: 2,
                                fontFamily: "'Fira Code', monospace",
                                color: it.tone === 'bad' ? 'var(--color-danger)'
                                    : it.tone === 'warn' ? 'var(--color-warning)'
                                    : it.tone === 'good' ? 'var(--color-success)'
                                    : 'var(--text-primary)',
                            }}>
                                {it.value}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function ClosedLoopStep({ n, label, detail, tone }: {
    n: number; label: string; detail: string; tone: 'good' | 'warn' | 'bad';
}) {
    const color = tone === 'bad' ? 'var(--color-danger)'
        : tone === 'warn' ? 'var(--color-warning)' : 'var(--color-success)';
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '8px 12px',
            background: 'var(--bg-elevated)',
            border: `1px solid var(--border)`,
            borderRadius: 8,
            minWidth: 200,
        }}>
            <div style={{
                width: 28, height: 28, borderRadius: '50%',
                background: color, color: '#000',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 800, fontSize: 13, flexShrink: 0,
            }}>
                {n}
            </div>
            <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>{label}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{detail}</div>
            </div>
        </div>
    );
}

function Arrow() {
    return (
        <span style={{ color: 'var(--text-muted)', fontSize: 18, fontWeight: 700 }}>{'→'}</span>
    );
}

function RosterRow({ icon, name, scope }: { icon: string; name: string; scope: string }) {
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '8px 10px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 6,
        }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--brand-primary)', flexShrink: 0 }}>
                {icon}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>{name}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {scope}
                </div>
            </div>
        </div>
    );
}
