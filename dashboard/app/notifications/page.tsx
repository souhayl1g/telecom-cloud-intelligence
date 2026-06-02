"use client";

import { useEffect, useState, useCallback } from "react";
import { Send, Mail, MessageSquare, AlertOctagon, FileText } from "lucide-react";

import StatTile from "../../components/ui/StatTile";
import SectionHeader from "../../components/ui/SectionHeader";
import EmptyState from "../../components/ui/EmptyState";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonTable, SkeletonStatCard } from "../../components/ui/LoadingSkeleton";
import { formatTunisDateTime } from "../../lib/time";

interface NotifRow {
    id: number;
    channel: "sms" | "email" | "console";
    recipient: string;
    subject: string | null;
    body: string;
    provider: string | null;
    provider_msg_id: string | null;
    status: "sent" | "failed" | "logged";
    error: string | null;
    source_action_id: string | null;
    source_imsi_hash: string | null;
    sent_at: string;
}

interface Stats {
    sms_count?: number;
    email_count?: number;
    sent_count?: number;
    failed_count?: number;
    logged_count?: number;
    total?: number;
    unique_recipients?: number;
}

export default function NotificationsPage() {
    const [rows, setRows] = useState<NotifRow[]>([]);
    const [stats, setStats] = useState<Stats>({});
    const [channelFilter, setChannelFilter] = useState<string>("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const qs = channelFilter ? `?channel=${encodeURIComponent(channelFilter)}` : "";
            const r = await fetch(`/api/notifications${qs}`, { cache: "no-store" });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const json = await r.json();
            setRows(json.notifications ?? []);
            setStats(json.stats ?? {});
        } catch (e: any) {
            setError(String(e?.message ?? e));
        } finally {
            setLoading(false);
        }
    }, [channelFilter]);

    useEffect(() => { load(); }, [load]);

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={Send}
                title="Notification Audit"
                subtitle="Every SMS/email dispatched by the L4 Agent is logged here (24h window in tiles)."
                tone="default"
            />

            {loading ? (
                <div className="grid grid-4">
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                </div>
            ) : (
                <div className="grid grid-4">
                    <StatTile label="SMS sent (24h)" value={stats.sms_count ?? 0} icon={MessageSquare} tone="info" />
                    <StatTile label="Email sent (24h)" value={stats.email_count ?? 0} icon={Mail} tone="info" />
                    <StatTile label="Delivery success" value={stats.sent_count ?? 0} icon={Send} tone="success" sub={`logged: ${stats.logged_count ?? 0}`} />
                    <StatTile label="Failed" value={stats.failed_count ?? 0} icon={AlertOctagon} tone="danger" />
                </div>
            )}

            <div className="card card-compact" style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>CHANNEL:</span>
                {["", "sms", "email", "console"].map(c => (
                    <button
                        key={c || "all"}
                        className={`badge ${channelFilter === c ? "badge-cyan" : ""}`}
                        style={{ cursor: "pointer", padding: "4px 10px", fontSize: 11 }}
                        onClick={() => setChannelFilter(c)}
                    >
                        {c || "all"}
                    </button>
                ))}
            </div>

            {error && <ErrorState title="Failed to load notifications" message={error} onRetry={load} />}
            {!error && loading && <SkeletonTable rows={8} />}

            {!error && !loading && rows.length === 0 && (
                <EmptyState
                    icon={FileText}
                    title="No notifications yet"
                    description="Run a pb-alert-subscriber or pb-churn-prevention playbook to generate notifications."
                />
            )}

            {!error && !loading && rows.length > 0 && (
                <div className="card">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>When</th>
                                <th>Channel</th>
                                <th>Provider</th>
                                <th>Recipient</th>
                                <th>Status</th>
                                <th>Body</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map(r => (
                                <tr key={r.id}>
                                    <td className="mono" style={{ fontSize: 11 }}>{formatTunisDateTime(r.sent_at)}</td>
                                    <td>
                                        <span className={`badge ${r.channel === "sms" ? "badge-cyan" : r.channel === "email" ? "badge-info" : "badge-warning"}`}>
                                            {r.channel}
                                        </span>
                                    </td>
                                    <td className="mono" style={{ fontSize: 11 }}>{r.provider ?? "—"}</td>
                                    <td className="mono" style={{ fontSize: 11 }}>{r.recipient.length > 20 ? r.recipient.slice(0, 18) + "…" : r.recipient}</td>
                                    <td>
                                        <span className={`badge ${r.status === "sent" ? "badge-success" : r.status === "failed" ? "badge-danger" : "badge-warning"}`}>
                                            {r.status}
                                        </span>
                                    </td>
                                    <td style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                                        {r.body.length > 80 ? r.body.slice(0, 78) + "…" : r.body}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
