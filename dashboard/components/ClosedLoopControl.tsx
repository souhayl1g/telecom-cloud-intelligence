"use client";

/**
 * ClosedLoopControl — the L4 safety envelope, made operable on stage.
 *
 * This is what turns the L3 (human-approved) agent into a genuine L4 closed loop.
 * The human owns the envelope here; the machine executes inside it:
 *
 *   armed                → master switch (nothing self-runs unless TRUE)
 *   playbook_whitelist   → ONLY these playbooks may self-execute (empty ⇒ none)
 *   confidence_threshold → minimum model confidence to act unattended
 *   max_actions_per_hour → rate limit so the loop cannot run away
 *   kill_switch          → emergency stop for the autonomous path
 *
 * All guardrails are ENFORCED server-side (PATCH /autonomy/config + POST
 * /autonomy/auto-run). This component only reflects + edits that envelope.
 */

export interface AutonomyConfig {
    armed: boolean;
    confidence_threshold: number;
    playbook_whitelist: string[];
    max_actions_per_hour: number;
    kill_switch: boolean;
    updated_by?: string | null;
    updated_at?: string | null;
}

export interface AutoRunResult {
    armed?: boolean;
    kill_switch?: boolean;
    executed?: { action_id: string; playbook_id?: string; title?: string }[];
    skipped?: { action_id: string; reason: string }[];
    rate_limit_remaining?: number;
    reason?: string;
}

// Playbooks the L4 action generator actually binds — the only ones worth whitelisting.
const KNOWN_PLAYBOOKS: { id: string; label: string }[] = [
    { id: "pb-anomaly-triage", label: "Anomaly Triage" },
    { id: "pb-create-ticket", label: "Open NOC Ticket" },
    { id: "pb-cem-degradation", label: "CEM Degradation" },
    { id: "pb-revenue-protect", label: "RAT / Revenue Protect" },
    { id: "pb-churn-prevention", label: "Churn Prevention" },
];

interface Props {
    config: AutonomyConfig | null;
    lastRun: AutoRunResult | null;
    busy: boolean;
    onPatch: (patch: Partial<AutonomyConfig>) => void;
    onRunNow: () => void;
}

export default function ClosedLoopControl({ config, lastRun, busy, onPatch, onRunNow }: Props) {
    const armed = !!config?.armed;
    const kill = !!config?.kill_switch;
    const whitelist = config?.playbook_whitelist ?? [];
    const threshold = config?.confidence_threshold ?? 0.85;
    const rate = config?.max_actions_per_hour ?? 10;

    const togglePlaybook = (id: string) => {
        const next = whitelist.includes(id)
            ? whitelist.filter((p) => p !== id)
            : [...whitelist, id];
        onPatch({ playbook_whitelist: next });
    };

    // Loop is live only when armed AND not killed AND at least one playbook authorised.
    const live = armed && !kill && whitelist.length > 0;
    const statusLabel = kill
        ? "KILL-SWITCH ENGAGED"
        : !armed
            ? "DISARMED"
            : whitelist.length === 0
                ? "ARMED · NO PLAYBOOKS AUTHORISED"
                : "CLOSED LOOP LIVE";
    const statusColor = kill
        ? "var(--color-danger, #DC2626)"
        : live
            ? "var(--color-success, #10B981)"
            : "var(--color-warning, #F59E0B)";

    return (
        <div className="card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 16 }}>
            {/* ── Header: status + master arm + kill ─────────────────── */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span
                        style={{
                            width: 10, height: 10, borderRadius: "50%", background: statusColor,
                            boxShadow: live ? `0 0 10px ${statusColor}` : "none",
                            animation: live ? "pulse 1.6s ease-in-out infinite" : "none",
                        }}
                    />
                    <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: 0.8, color: statusColor }}>
                        {statusLabel}
                    </span>
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                        · L4 closed-loop autonomy envelope
                    </span>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <button
                        className={`l4-btn ${armed ? "l4-btn-reject" : "l4-btn-approve"}`}
                        disabled={busy || kill}
                        onClick={() => onPatch({ armed: !armed })}
                        title={kill ? "Disengage kill-switch first" : armed ? "Disarm the closed loop" : "Arm the closed loop"}
                    >
                        {armed ? "Disarm" : "Arm Closed Loop"}
                    </button>
                    <button
                        className="l4-btn"
                        disabled={busy}
                        onClick={() => onPatch({ kill_switch: !kill })}
                        style={{
                            background: kill ? "var(--color-danger, #DC2626)" : "transparent",
                            color: kill ? "#fff" : "var(--color-danger, #DC2626)",
                            border: "1px solid var(--color-danger, #DC2626)",
                        }}
                        title="Emergency stop for the autonomous path (manual approvals still work)"
                    >
                        {kill ? "Disengage Kill" : "Kill-Switch"}
                    </button>
                </div>
            </div>

            {/* ── Envelope controls ───────────────────────────────────── */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {/* Confidence threshold */}
                <div>
                    <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.6 }}>
                        Confidence threshold · {(threshold * 100).toFixed(0)}%
                    </label>
                    <input
                        type="range" min={0} max={1} step={0.01} value={threshold} disabled={busy}
                        onChange={(e) => onPatch({ confidence_threshold: parseFloat(e.target.value) })}
                        style={{ width: "100%", marginTop: 8, accentColor: "var(--color-success, #10B981)" }}
                    />
                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                        Only act on signals the models are at least this sure about.
                    </div>
                </div>
                {/* Rate limit */}
                <div>
                    <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.6 }}>
                        Max autonomous actions / hour
                    </label>
                    <input
                        type="number" min={0} max={100} value={rate} disabled={busy}
                        onChange={(e) => onPatch({ max_actions_per_hour: parseInt(e.target.value || "0", 10) })}
                        style={{
                            width: "100%", marginTop: 8, padding: "8px 10px", borderRadius: 8,
                            background: "var(--glass-bg, rgba(255,255,255,0.04))",
                            border: "1px solid var(--glass-border, rgba(255,255,255,0.1))",
                            color: "inherit", fontSize: 14,
                        }}
                    />
                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                        Hard cap — the loop refuses once the trailing hour hits this.
                    </div>
                </div>
            </div>

            {/* ── Playbook whitelist (the authority surface) ──────────── */}
            <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.6 }}>
                    Authorised playbooks · {whitelist.length} of {KNOWN_PLAYBOOKS.length}
                </label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
                    {KNOWN_PLAYBOOKS.map((pb) => {
                        const on = whitelist.includes(pb.id);
                        return (
                            <button
                                key={pb.id}
                                disabled={busy}
                                onClick={() => togglePlaybook(pb.id)}
                                style={{
                                    padding: "6px 12px", borderRadius: 999, fontSize: 12, fontWeight: 600,
                                    cursor: busy ? "default" : "pointer",
                                    background: on ? "var(--color-success, #10B981)" : "transparent",
                                    color: on ? "#06281c" : "var(--text-muted)",
                                    border: `1px solid ${on ? "var(--color-success, #10B981)" : "var(--glass-border, rgba(255,255,255,0.18))"}`,
                                    transition: "all 0.15s ease",
                                }}
                                title={pb.id}
                            >
                                {on ? "✓ " : "+ "}{pb.label}
                            </button>
                        );
                    })}
                </div>
                {whitelist.length === 0 && (
                    <div style={{ fontSize: 11, color: "var(--color-warning, #F59E0B)", marginTop: 8 }}>
                        Empty whitelist → nothing self-executes. Arming alone is inert until you authorise a playbook.
                    </div>
                )}
            </div>

            {/* ── Manual tick + last-run verdicts ─────────────────────── */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap", borderTop: "1px solid var(--glass-border, rgba(255,255,255,0.08))", paddingTop: 12 }}>
                <button className="l4-btn l4-btn-approve" disabled={busy || !live} onClick={onRunNow}
                    title={live ? "Run the closed-loop tick now" : "Arm + authorise a playbook first"}>
                    {busy ? "Running…" : "Run Closed-Loop Tick"}
                </button>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    {lastRun
                        ? lastRun.reason
                            ? `Last tick: ${lastRun.reason}`
                            : `Last tick: ${lastRun.executed?.length ?? 0} executed · ${lastRun.skipped?.length ?? 0} skipped${
                                  lastRun.rate_limit_remaining !== undefined ? ` · ${lastRun.rate_limit_remaining} left this hour` : ""
                              }`
                        : "Auto-runs every 30s poll while live."}
                </div>
            </div>

            {/* Show what the machine just did (audit transparency) */}
            {lastRun?.executed && lastRun.executed.length > 0 && (
                <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }}>
                    {lastRun.executed.map((e) => (
                        <div key={e.action_id} style={{ color: "var(--color-success, #10B981)" }}>
                            ✓ executed <strong>{e.title ?? e.action_id}</strong>
                            {e.playbook_id ? ` via ${e.playbook_id}` : ""}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
