"use client";
import { useMemo, useState } from "react";

/* ── Real-time Anomaly Timeline ───────────────────────────────────────────
   Merges OSS + BSS anomalies into a single chronological event stream,
   color-coded by severity, filterable by domain and level.
   ──────────────────────────────────────────────────────────────────────── */

interface TimelineEvent {
    id: string;
    domain: "OSS" | "BSS";
    severity: number;
    level: "critical" | "warning" | "low";
    title: string;
    detail: string;
    region: string;
    timestamp: Date;
    raw: any;
}

interface AnomalyTimelineProps {
    ossAnomalies: any[];
    bssAnomalies: any[];
}

function classifyLevel(sev: number): "critical" | "warning" | "low" {
    if (sev > 0.9) return "critical";
    if (sev > 0.5) return "warning";
    return "low";
}

function parseTs(a: any): Date {
    if (a.created_at) return new Date(a.created_at);
    if (a.ts) return new Date(a.ts);
    return new Date();
}

function buildEvents(oss: any[], bss: any[]): TimelineEvent[] {
    const events: TimelineEvent[] = [];

    oss.forEach((a, i) => {
        const sev = a.severity ?? 0;
        const deviation = a.value != null && a.baseline_value != null && a.baseline_value !== 0
            ? ((a.value - a.baseline_value) / Math.abs(a.baseline_value) * 100).toFixed(1)
            : null;
        events.push({
            id: `oss-${i}`,
            domain: "OSS",
            severity: sev,
            level: classifyLevel(sev),
            title: `${a.cell_id ?? "Unknown"} \u2014 ${(a.kpi_name ?? "composite").replace(/_/g, " ")}`,
            detail: `Severity ${sev.toFixed(2)}${deviation ? ` | ${Number(deviation) > 0 ? "+" : ""}${deviation}% from baseline` : ""}${a.value != null ? ` | Value: ${Number(a.value).toFixed(2)}` : ""}`,
            region: a.region ?? "unknown",
            timestamp: parseTs(a),
            raw: a,
        });
    });

    bss.forEach((a, i) => {
        const sev = a.severity ?? a.score ?? 0;
        events.push({
            id: `bss-${i}`,
            domain: "BSS",
            severity: sev,
            level: classifyLevel(sev),
            title: `${a.operator ?? "Unknown"} \u2014 ${(a.metric_name ?? "revenue").replace(/_/g, " ")}`,
            detail: `Severity ${sev.toFixed(2)} | ${a.line_type ?? "unknown"} | ${a.plan ?? "N/A"}${a.value != null ? ` | Value: ${Number(a.value).toFixed(2)}` : ""}`,
            region: a.region ?? "unknown",
            timestamp: parseTs(a),
            raw: a,
        });
    });

    return events.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
}

/* ── Component ────────────────────────────────────────────────────────────── */
export default function AnomalyTimeline({ ossAnomalies, bssAnomalies }: AnomalyTimelineProps) {
    const [domainFilter, setDomainFilter] = useState<"all" | "OSS" | "BSS">("all");
    const [levelFilter, setLevelFilter] = useState<"all" | "critical" | "warning" | "low">("all");
    const [limit, setLimit] = useState(30);

    const allEvents = useMemo(() => buildEvents(ossAnomalies, bssAnomalies), [ossAnomalies, bssAnomalies]);

    const filtered = useMemo(() => {
        return allEvents
            .filter((e) => domainFilter === "all" || e.domain === domainFilter)
            .filter((e) => levelFilter === "all" || e.level === levelFilter);
    }, [allEvents, domainFilter, levelFilter]);

    const visible = filtered.slice(0, limit);

    // Stats
    const stats = useMemo(() => ({
        total: allEvents.length,
        critical: allEvents.filter((e) => e.level === "critical").length,
        warning: allEvents.filter((e) => e.level === "warning").length,
        low: allEvents.filter((e) => e.level === "low").length,
        oss: allEvents.filter((e) => e.domain === "OSS").length,
        bss: allEvents.filter((e) => e.domain === "BSS").length,
    }), [allEvents]);

    return (
        <div className="tl-panel">
            {/* Controls bar */}
            <div className="tl-controls">
                <div className="tl-filter-group">
                    <span className="tl-filter-label">Domain</span>
                    {(["all", "OSS", "BSS"] as const).map((d) => (
                        <button
                            key={d}
                            className={`tl-filter-btn ${domainFilter === d ? "tl-filter-active" : ""}`}
                            onClick={() => setDomainFilter(d)}
                        >
                            {d === "all" ? `All (${stats.total})` : `${d} (${d === "OSS" ? stats.oss : stats.bss})`}
                        </button>
                    ))}
                </div>
                <div className="tl-filter-group">
                    <span className="tl-filter-label">Severity</span>
                    {(["all", "critical", "warning", "low"] as const).map((l) => (
                        <button
                            key={l}
                            className={`tl-filter-btn tl-sev-${l} ${levelFilter === l ? "tl-filter-active" : ""}`}
                            onClick={() => setLevelFilter(l)}
                        >
                            {l === "all" ? "All" : `${l.charAt(0).toUpperCase() + l.slice(1)} (${stats[l as keyof typeof stats]})`}
                        </button>
                    ))}
                </div>
            </div>

            {/* Severity mini-bar */}
            <div className="tl-severity-bar">
                <div className="tl-sev-segment tl-sev-critical-bg" style={{ flex: stats.critical }} title={`${stats.critical} critical`} />
                <div className="tl-sev-segment tl-sev-warning-bg" style={{ flex: stats.warning }} title={`${stats.warning} warning`} />
                <div className="tl-sev-segment tl-sev-low-bg" style={{ flex: stats.low }} title={`${stats.low} low`} />
            </div>

            {/* Timeline */}
            <div className="tl-stream">
                {visible.length === 0 && (
                    <div className="tl-empty">No anomalies match the current filters.</div>
                )}
                {visible.map((event, idx) => (
                    <div key={event.id} className={`tl-event tl-event-${event.level}`}>
                        {/* Connector line */}
                        <div className="tl-connector">
                            <div className={`tl-dot tl-dot-${event.level}`} />
                            {idx < visible.length - 1 && <div className="tl-line" />}
                        </div>

                        {/* Content */}
                        <div className="tl-content">
                            <div className="tl-event-header">
                                <span className={`tl-domain-tag tl-domain-${event.domain.toLowerCase()}`}>
                                    {event.domain}
                                </span>
                                <span className={`tl-level-tag tl-level-${event.level}`}>
                                    {event.level.toUpperCase()}
                                </span>
                                <span className="tl-region">{event.region}</span>
                                <span className="tl-time">
                                    {event.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                                </span>
                            </div>
                            <div className="tl-event-title">{event.title}</div>
                            <div className="tl-event-detail">{event.detail}</div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Load more */}
            {filtered.length > limit && (
                <button className="tl-load-more" onClick={() => setLimit((l) => l + 30)}>
                    Show more ({filtered.length - limit} remaining)
                </button>
            )}
        </div>
    );
}
