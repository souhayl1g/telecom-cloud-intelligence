"use client";

import { useEffect, useState, useCallback } from "react";
import { ShieldCheck, TrendingUp, Pause, AlertOctagon, Users, Info, Play } from "lucide-react";

import StatTile from "../../components/ui/StatTile";
import SectionHeader from "../../components/ui/SectionHeader";
import EmptyState from "../../components/ui/EmptyState";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonTable, SkeletonStatCard } from "../../components/ui/LoadingSkeleton";
import { formatTunisDateTime } from "../../lib/time";

interface Intervention {
    id: number;
    intervention_id: string;
    imsi_hash: string;
    intervention_type: string;
    cem_at_intervention: number | null;
    rat_gap_at_intervention: number | null;
    follow_up_cem: number | null;
    follow_up_checked_at: string | null;
    outcome: "pending" | "improved" | "no_change" | "worsened";
    source_action_id: string | null;
    created_at: string;
}

interface Stats {
    total?: number;
    pending?: number;
    improved?: number;
    no_change?: number;
    worsened?: number;
    avg_cem_delta?: number | null;
    sms_count?: number;
    sim_count?: number;
    plan_count?: number;
    ticket_count?: number;
    daily?: { day: string; count: number; improved: number }[];
}

const OUTCOME_TONE: Record<string, "success" | "info" | "warning" | "danger"> = {
    improved: "success",
    no_change: "info",
    worsened: "danger",
    pending: "warning",
};

export default function InterventionsPage() {
    const [rows, setRows] = useState<Intervention[]>([]);
    const [stats, setStats] = useState<Stats>({});
    const [outcomeFilter, setOutcomeFilter] = useState<string>("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sweeping, setSweeping] = useState(false);
    const [sweepResult, setSweepResult] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const qs = outcomeFilter ? `?outcome=${encodeURIComponent(outcomeFilter)}` : "";
            const r = await fetch(`/api/interventions${qs}`, { cache: "no-store" });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const json = await r.json();
            setRows(json.interventions ?? []);
            setStats(json.stats ?? {});
        } catch (e: any) {
            setError(String(e?.message ?? e));
        } finally {
            setLoading(false);
        }
    }, [outcomeFilter]);

    useEffect(() => { load(); }, [load]);

    const runPreventionSweep = useCallback(async () => {
        setSweeping(true);
        setSweepResult(null);
        try {
            const action_id = `cmdk-pb-churn-prevention-${Date.now()}`;
            const createRes = await fetch("/api/platform-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    _action: "create",
                    action_id,
                    title: "Manual churn-prevention sweep",
                    severity: "warning",
                    type: "remediation",
                    confidence: 0.95,
                    playbook_id: "pb-churn-prevention",
                    description: "Manual churn-prevention sweep (interventions page)",
                    metadata: { limit: 100 },
                }),
            });
            if (!createRes.ok) throw new Error(`create HTTP ${createRes.status}`);
            const execRes = await fetch("/api/platform-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ _action: "execute", action_id }),
            });
            if (!execRes.ok) throw new Error(`execute HTTP ${execRes.status}`);
            setSweepResult("Sweep fired — refreshing...");
            await load();
        } catch (e: any) {
            setSweepResult(`Failed: ${String(e?.message ?? e)}`);
        } finally {
            setSweeping(false);
        }
    }, [load]);

    const successRate = stats.total
        ? Math.round(((stats.improved ?? 0) / Math.max(1, (stats.total ?? 1) - (stats.pending ?? 0))) * 100)
        : 0;

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={ShieldCheck}
                title="Churn Interventions — Longitudinal Outcomes"
                subtitle="Every intervention sent by pb-churn-prevention is tracked here. Pipeline-worker re-checks CEM 2h later and classifies the outcome."
                tone="default"
            />

            {/* How interventions work — explainer card */}
            <div
                className="card"
                style={{
                    padding: 16,
                    background: "linear-gradient(135deg, rgba(56,189,248,0.08), rgba(14,165,233,0.02))",
                    border: "1px solid rgba(56,189,248,0.25)",
                }}
            >
                <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <Info size={18} style={{ color: "var(--color-info, #38bdf8)", flexShrink: 0, marginTop: 2 }} />
                    <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
                            How an intervention is born
                        </div>
                        <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12, lineHeight: 1.6, color: "var(--text-muted)" }}>
                            <li>
                                <strong>Trigger:</strong> <code>pb-churn-prevention</code> playbook queries <code>subscriber_features</code> for
                                subscribers where <code>rat_gap_score &gt; 0.5</code> AND <code>cem_score &lt; 0.3</code> — i.e. dropping experience
                                + frustrating RAT gap.
                            </li>
                            <li>
                                <strong>Action:</strong> For each at-risk subscriber: send a personalized SMS offer (sim_upgrade_offer if usim_bottleneck=true, else sms_offer / plan_upgrade).
                                One row inserted into <code>churn_interventions</code> with <code>outcome=&apos;pending&apos;</code>.
                            </li>
                            <li>
                                <strong>Follow-up:</strong> Pipeline-worker re-reads CEM after a grace window (default 2 h, env <code>INTERVENTION_GRACE_MINUTES</code>),
                                writes <code>follow_up_cem</code>, classifies outcome as <strong>improved</strong> (Δ ≥ +0.05),
                                <strong> no_change</strong>, or <strong>worsened</strong> (Δ ≤ −0.05).
                            </li>
                            <li>
                                <strong>Why zeros now:</strong> Tables stay empty until at least one sweep fires. Click below or run from Cmd+K → Run Playbook.
                            </li>
                        </ol>
                        <div style={{ marginTop: 12, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                            <button
                                className="l4-btn l4-btn-approve"
                                style={{ padding: "8px 14px", fontSize: 12, display: "inline-flex", alignItems: "center", gap: 6 }}
                                onClick={runPreventionSweep}
                                disabled={sweeping}
                            >
                                <Play size={12} />
                                {sweeping ? "Sweeping..." : "Run prevention sweep now"}
                            </button>
                            {sweepResult && (
                                <span style={{ fontSize: 11, color: sweepResult.startsWith("Failed") ? "var(--color-danger)" : "var(--color-success)" }}>
                                    {sweepResult}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="grid grid-4">
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                </div>
            ) : (
                <div className="grid grid-4">
                    <StatTile label="Pending" value={stats.pending ?? 0} icon={Pause} tone="warning" sub="Awaiting CEM follow-up" />
                    <StatTile label="Improved" value={stats.improved ?? 0} icon={TrendingUp} tone="success" sub={`Success rate ${successRate}%`} />
                    <StatTile label="No change" value={stats.no_change ?? 0} icon={Users} tone="info" />
                    <StatTile label="Worsened" value={stats.worsened ?? 0} icon={AlertOctagon} tone="danger" />
                </div>
            )}

            {/* Intervention type breakdown */}
            {!loading && !error && stats.total && stats.total > 0 && (
                <div className="grid grid-4">
                    <StatTile label="SMS offers" value={stats.sms_count ?? 0} tone="info" />
                    <StatTile label="SIM upgrade offers" value={stats.sim_count ?? 0} tone="info" />
                    <StatTile label="Plan upgrades" value={stats.plan_count ?? 0} tone="info" />
                    <StatTile label="Tickets opened" value={stats.ticket_count ?? 0} tone="info" />
                </div>
            )}

            <div className="card card-compact" style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>OUTCOME:</span>
                {["", "pending", "improved", "no_change", "worsened"].map(o => (
                    <button
                        key={o || "all"}
                        className={`badge ${outcomeFilter === o ? "badge-cyan" : ""}`}
                        style={{ cursor: "pointer", padding: "4px 10px", fontSize: 11 }}
                        onClick={() => setOutcomeFilter(o)}
                    >
                        {o || "all"}
                    </button>
                ))}
                {stats.avg_cem_delta !== null && stats.avg_cem_delta !== undefined && (
                    <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-muted)" }}>
                        Avg ΔCEM (resolved interventions):{" "}
                        <strong style={{ color: stats.avg_cem_delta >= 0 ? "var(--color-success)" : "var(--color-danger)" }}>
                            {stats.avg_cem_delta >= 0 ? "+" : ""}{Number(stats.avg_cem_delta).toFixed(4)}
                        </strong>
                    </span>
                )}
            </div>

            {error && <ErrorState title="Failed to load interventions" message={error} onRetry={load} />}
            {!error && loading && <SkeletonTable rows={8} />}

            {!error && !loading && rows.length === 0 && (
                <EmptyState
                    icon={ShieldCheck}
                    title="No interventions yet"
                    description="Run pb-churn-prevention from the L4 Agent → Playbooks tab to start tracking outcomes."
                />
            )}

            {!error && !loading && rows.length > 0 && (
                <div className="card">
                    <table className="table">
                        <thead>
                            <tr>
                                <th title="When the intervention was issued (pb-churn-prevention insert).">When</th>
                                <th title="Salted SHA-256 IMSI hash. Cannot be reversed to a phone number — privacy by design.">Subscriber (IMSI)</th>
                                <th title="sms_offer = generic; sim_upgrade_offer = device USIM bottleneck; plan_upgrade = tariff change.">Type</th>
                                <th title="CEM score (0..1) at the moment the intervention fired. Lower = worse experience.">CEM @ start</th>
                                <th title="RAT underservice gap (0..1) at intervention time. >0.5 means RAT capability lags peers.">RAT gap</th>
                                <th title="CEM score re-measured after the grace window (INTERVENTION_GRACE_MINUTES, default 120m).">Follow-up CEM</th>
                                <th title="follow_up_cem − cem_at_intervention. Positive (green) = improved.">Δ CEM</th>
                                <th title="improved (Δ ≥ +0.05) | no_change | worsened (Δ ≤ −0.05) | pending (not yet re-measured).">Outcome</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map(r => {
                                const delta = r.follow_up_cem !== null && r.cem_at_intervention !== null
                                    ? r.follow_up_cem - r.cem_at_intervention
                                    : null;
                                return (
                                    <tr key={r.id}>
                                        <td className="mono" style={{ fontSize: 11 }}>{formatTunisDateTime(r.created_at)}</td>
                                        <td className="mono" style={{ fontSize: 11 }}>{r.imsi_hash.slice(0, 18)}…</td>
                                        <td>
                                            <span className="badge badge-info">{r.intervention_type}</span>
                                        </td>
                                        <td className="mono">{r.cem_at_intervention !== null ? Number(r.cem_at_intervention).toFixed(4) : "—"}</td>
                                        <td className="mono">{r.rat_gap_at_intervention !== null ? Number(r.rat_gap_at_intervention).toFixed(3) : "—"}</td>
                                        <td className="mono">{r.follow_up_cem !== null ? Number(r.follow_up_cem).toFixed(4) : "—"}</td>
                                        <td className="mono" style={{ color: delta === null ? undefined : delta >= 0 ? "var(--color-success)" : "var(--color-danger)" }}>
                                            {delta === null ? "—" : `${delta >= 0 ? "+" : ""}${delta.toFixed(4)}`}
                                        </td>
                                        <td>
                                            <span className={`badge badge-${OUTCOME_TONE[r.outcome] ?? "info"}`}>{r.outcome}</span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
