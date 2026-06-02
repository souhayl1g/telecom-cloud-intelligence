"use client";

import { useEffect, useState, useCallback } from "react";
import { Ticket, AlertOctagon, Clock, CheckCircle2 } from "lucide-react";

import StatTile from "../../components/ui/StatTile";
import SectionHeader from "../../components/ui/SectionHeader";
import EmptyState from "../../components/ui/EmptyState";
import ErrorState from "../../components/ui/ErrorState";
import Drawer from "../../components/ui/Drawer";
import { SkeletonTable, SkeletonStatCard } from "../../components/ui/LoadingSkeleton";
import { formatTunisDateTime } from "../../lib/time";

interface TicketRow {
    ticket_id: string;
    title: string;
    description: string | null;
    severity: "critical" | "warning" | "info";
    status: "open" | "in_progress" | "resolved" | "closed";
    cell_id: string | null;
    area: string | null;
    assigned_to: string | null;
    source_action_id: string | null;
    metadata: any;
    created_at: string;
    resolved_at: string | null;
}

interface Stats {
    open_count?: number;
    in_progress_count?: number;
    resolved_count?: number;
    closed_count?: number;
    critical_count?: number;
    warning_count?: number;
    info_count?: number;
    total?: number;
}

const SEVERITY_COLOR: Record<string, "danger" | "warning" | "info"> = {
    critical: "danger",
    warning: "warning",
    info: "info",
};

export default function TicketsPage() {
    const [tickets, setTickets] = useState<TicketRow[]>([]);
    const [stats, setStats] = useState<Stats>({});
    const [filterStatus, setFilterStatus] = useState<string>("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selected, setSelected] = useState<TicketRow | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const qs = filterStatus ? `?status=${encodeURIComponent(filterStatus)}` : "";
            const r = await fetch(`/api/tickets${qs}`, { cache: "no-store" });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const json = await r.json();
            setTickets(json.tickets ?? []);
            setStats(json.stats ?? {});
        } catch (e: any) {
            setError(String(e?.message ?? e));
        } finally {
            setLoading(false);
        }
    }, [filterStatus]);

    useEffect(() => {
        load();
    }, [load]);

    const patchStatus = async (ticket_id: string, next: string) => {
        await fetch(`/api/tickets/${ticket_id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: next }),
        });
        load();
    };

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={Ticket}
                title="NOC Tickets"
                subtitle="Internal incident tracking. Auto-opened by L4 Agent or created manually."
                tone="default"
            />

            {/* KPI tiles */}
            {loading ? (
                <div className="grid grid-4">
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                    <SkeletonStatCard />
                </div>
            ) : (
                <div className="grid grid-4">
                    <StatTile label="Open" value={stats.open_count ?? 0} icon={Clock} tone="warning" />
                    <StatTile label="In Progress" value={stats.in_progress_count ?? 0} icon={Ticket} tone="info" />
                    <StatTile label="Resolved" value={stats.resolved_count ?? 0} icon={CheckCircle2} tone="success" />
                    <StatTile label="Critical" value={stats.critical_count ?? 0} icon={AlertOctagon} tone="danger" />
                </div>
            )}

            {/* Filter bar */}
            <div className="card card-compact" style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>STATUS:</span>
                {["", "open", "in_progress", "resolved", "closed"].map(s => (
                    <button
                        key={s || "all"}
                        className={`badge ${filterStatus === s ? "badge-cyan" : ""}`}
                        style={{ cursor: "pointer", padding: "4px 10px", fontSize: 11 }}
                        onClick={() => setFilterStatus(s)}
                    >
                        {s || "all"}
                    </button>
                ))}
            </div>

            {error && (
                <ErrorState
                    title="Failed to load tickets"
                    message={error}
                    onRetry={load}
                />
            )}

            {!error && loading && <SkeletonTable rows={8} />}

            {!error && !loading && tickets.length === 0 && (
                <EmptyState
                    icon={Ticket}
                    title="No tickets yet"
                    description="Tickets are auto-created by the L4 Agent (pb-create-ticket) when critical signals fire."
                />
            )}

            {!error && !loading && tickets.length > 0 && (
                <div className="card">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Ticket</th>
                                <th>Title</th>
                                <th>Severity</th>
                                <th>Status</th>
                                <th>Area</th>
                                <th>Cell</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tickets.map(t => (
                                <tr
                                    key={t.ticket_id}
                                    onClick={() => setSelected(t)}
                                    style={{ cursor: "pointer" }}
                                    title="Click to preview ticket"
                                >
                                    <td className="mono">{t.ticket_id}</td>
                                    <td>{t.title}</td>
                                    <td>
                                        <span className={`badge badge-${SEVERITY_COLOR[t.severity] ?? "info"}`}>
                                            {t.severity}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`badge ${t.status === "open" ? "badge-warning" : t.status === "resolved" || t.status === "closed" ? "badge-success" : "badge-cyan"}`}>
                                            {t.status}
                                        </span>
                                    </td>
                                    <td className="mono">{t.area ?? "—"}</td>
                                    <td className="mono">{t.cell_id ?? "—"}</td>
                                    <td className="mono" style={{ fontSize: 11 }}>
                                        {formatTunisDateTime(t.created_at)}
                                    </td>
                                    <td onClick={(e) => e.stopPropagation()}>
                                        {t.status === "open" && (
                                            <button className="l4-btn" style={{ padding: "4px 8px", fontSize: 10 }} onClick={() => patchStatus(t.ticket_id, "in_progress")}>
                                                Start
                                            </button>
                                        )}
                                        {t.status === "in_progress" && (
                                            <button className="l4-btn l4-btn-approve" style={{ padding: "4px 8px", fontSize: 10 }} onClick={() => patchStatus(t.ticket_id, "resolved")}>
                                                Resolve
                                            </button>
                                        )}
                                        {(t.status === "resolved" || t.status === "closed") && (
                                            <span style={{ color: "var(--text-muted)", fontSize: 11 }}>—</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <Drawer
                open={!!selected}
                onClose={() => setSelected(null)}
                title={selected?.title}
                subtitle={selected ? `${selected.ticket_id} · ${selected.severity} · ${selected.status}` : undefined}
            >
                {selected && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                        <section>
                            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>
                                Overview
                            </div>
                            <DetailRow label="Ticket ID" value={selected.ticket_id} mono />
                            <DetailRow label="Severity" value={selected.severity} />
                            <DetailRow label="Status" value={selected.status} />
                            <DetailRow label="Area" value={selected.area ?? "—"} mono />
                            <DetailRow label="Cell" value={selected.cell_id ?? "—"} mono />
                            <DetailRow label="Assigned to" value={selected.assigned_to ?? "—"} />
                            <DetailRow label="Source action" value={selected.source_action_id ?? "—"} mono />
                            <DetailRow label="Created" value={formatTunisDateTime(selected.created_at)} mono />
                            {selected.resolved_at && (
                                <DetailRow label="Resolved" value={formatTunisDateTime(selected.resolved_at)} mono />
                            )}
                        </section>

                        {selected.description && (
                            <section>
                                <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>
                                    Description
                                </div>
                                <p style={{ margin: 0, lineHeight: 1.5, color: "var(--text-primary)" }}>
                                    {selected.description}
                                </p>
                            </section>
                        )}

                        <section>
                            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>
                                Metadata (JSONB)
                            </div>
                            <pre
                                style={{
                                    margin: 0,
                                    padding: 12,
                                    background: "rgba(15,23,42,0.6)",
                                    border: "1px solid var(--border)",
                                    borderRadius: 6,
                                    fontSize: 11,
                                    lineHeight: 1.5,
                                    overflowX: "auto",
                                    whiteSpace: "pre-wrap",
                                    wordBreak: "break-word",
                                }}
                            >
                                {selected.metadata
                                    ? JSON.stringify(selected.metadata, null, 2)
                                    : "(empty)"}
                            </pre>
                        </section>

                        <section style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            {selected.status === "open" && (
                                <button
                                    className="l4-btn"
                                    style={{ padding: "8px 14px", fontSize: 12 }}
                                    onClick={() => {
                                        patchStatus(selected.ticket_id, "in_progress");
                                        setSelected(null);
                                    }}
                                >
                                    Start work
                                </button>
                            )}
                            {selected.status === "in_progress" && (
                                <button
                                    className="l4-btn l4-btn-approve"
                                    style={{ padding: "8px 14px", fontSize: 12 }}
                                    onClick={() => {
                                        patchStatus(selected.ticket_id, "resolved");
                                        setSelected(null);
                                    }}
                                >
                                    Resolve
                                </button>
                            )}
                            {(selected.status === "open" || selected.status === "in_progress") && (
                                <button
                                    className="l4-btn"
                                    style={{ padding: "8px 14px", fontSize: 12 }}
                                    onClick={() => {
                                        patchStatus(selected.ticket_id, "closed");
                                        setSelected(null);
                                    }}
                                >
                                    Close
                                </button>
                            )}
                        </section>
                    </div>
                )}
            </Drawer>
        </div>
    );
}

function DetailRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
    return (
        <div style={{ display: "flex", padding: "5px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
            <span style={{ flex: "0 0 130px", fontSize: 11, color: "var(--text-muted)" }}>{label}</span>
            <span
                className={mono ? "mono" : undefined}
                style={{ flex: 1, fontSize: 12, color: "var(--text-primary)", wordBreak: "break-word" }}
            >
                {value}
            </span>
        </div>
    );
}
