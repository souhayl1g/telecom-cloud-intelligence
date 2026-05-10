"use client";

import { useEffect, useMemo, useState } from "react";

interface LeadTimeRow {
    area: string;
    oss_variable?: string;
    cem_variable?: string;
    direction?: string;
    avg_lag: number;
    avg_lead_time_minutes: number;
    min_pvalue: number;
    significant_count: number;
    total: number;
}

interface LeadTimePayload {
    lag_window_minutes: number;
    area_filter: string | null;
    rows: LeadTimeRow[];
}

function fmtMinutes(min: number): string {
    if (!isFinite(min) || min <= 0) return "—";
    if (min < 60) return `${Math.round(min)} min`;
    if (min < 60 * 24) return `${(min / 60).toFixed(1)} h`;
    if (min < 60 * 24 * 30) return `${(min / 1440).toFixed(1)} d`;
    return `${(min / 43200).toFixed(1)} mo`;
}

export default function LeadTimeHistogram({ area }: { area?: string }) {
    const [payload, setPayload] = useState<LeadTimePayload | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const url = area
            ? `/api/granger-lead-time?area=${encodeURIComponent(area)}`
            : `/api/granger-lead-time`;
        fetch(url, { cache: "no-store" })
            .then((r) => (r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`)))
            .then(setPayload)
            .catch((e) => setError(String(e?.message || e)));
    }, [area]);

    const { headline, sorted } = useMemo(() => {
        const rows = payload?.rows ?? [];
        const valid = rows.filter((r) => isFinite(r.avg_lead_time_minutes));
        const total = valid.reduce((acc, r) => acc + r.avg_lead_time_minutes, 0);
        const headlineMin = valid.length ? total / valid.length : 0;
        const sorted = [...valid].sort((a, b) => a.avg_lead_time_minutes - b.avg_lead_time_minutes);
        return { headline: headlineMin, sorted };
    }, [payload]);

    if (error) {
        return (
            <div style={{ color: "var(--color-text-tertiary, #888)", fontSize: 13 }}>
                Lead-time data unavailable ({error}).
            </div>
        );
    }
    if (!payload) {
        return <div style={{ fontSize: 13, color: "#888" }}>Loading lead-time…</div>;
    }
    if (!sorted.length) {
        return <div style={{ fontSize: 13, color: "#888" }}>No Granger results yet — run the pipeline first.</div>;
    }

    const maxMin = Math.max(...sorted.map((r) => r.avg_lead_time_minutes), 1);

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span style={{ fontSize: 28, fontWeight: 700, color: "var(--color-purple, #a78bfa)" }}>
                    {fmtMinutes(headline)}
                </span>
                <span style={{ fontSize: 12, color: "#888" }}>
                    avg detection lead time across {sorted.length} {area ? "pairs" : "areas"}
                </span>
            </div>

            <div style={{ fontSize: 11, color: "#666", lineHeight: 1.5 }}>
                Lead time = Granger best lag × <code>{payload.lag_window_minutes}</code>min/window.
                Window inherited from <code>area_network_health</code> monthly grain;
                drop <code>LAG_WINDOW_MINUTES</code> on api-gateway once cycle-level Granger refresh is wired.
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {sorted.slice(0, 12).map((r, i) => {
                    const w = (r.avg_lead_time_minutes / maxMin) * 100;
                    const label = area ? `${r.oss_variable} → ${r.cem_variable}` : r.area;
                    return (
                        <div key={`${label}-${i}`} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ width: 180, fontSize: 11, fontFamily: "monospace", color: "#aaa" }}>
                                {label}
                            </span>
                            <div style={{ flex: 1, background: "rgba(167,139,250,0.1)", height: 14, borderRadius: 3, overflow: "hidden" }}>
                                <div
                                    style={{
                                        width: `${w}%`,
                                        height: "100%",
                                        background: "linear-gradient(90deg, #a78bfa, #6366f1)",
                                    }}
                                />
                            </div>
                            <span style={{ width: 80, textAlign: "right", fontSize: 11, color: "#ddd" }}>
                                {fmtMinutes(r.avg_lead_time_minutes)}
                            </span>
                            <span
                                style={{
                                    width: 60,
                                    textAlign: "right",
                                    fontSize: 10,
                                    color: r.significant_count > 0 ? "#10b981" : "#71717a",
                                }}
                            >
                                {r.significant_count}/{r.total} sig
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
