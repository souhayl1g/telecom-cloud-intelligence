"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { durationSeconds } from "../lib/time";

interface StripData {
    cycle: number | null;
    durationSec: number | null;
    openAnomalies: number;
    l4Online: boolean;
    pendingActions: number;
    lastRefreshAgo: string;
}

const REFRESH_MS = 30_000;

function timeAgo(ts: number): string {
    const sec = Math.floor((Date.now() - ts) / 1000);
    if (sec < 5) return "just now";
    if (sec < 60) return `${sec}s ago`;
    const min = Math.floor(sec / 60);
    return `${min}m ago`;
}

export default function StatusStrip() {
    const [data, setData] = useState<StripData>({
        cycle: null, durationSec: null, openAnomalies: 0,
        l4Online: true, pendingActions: 0, lastRefreshAgo: "—",
    });
    const [lastFetch, setLastFetch] = useState(Date.now());

    const refresh = async () => {
        try {
            const res = await fetch("/api/platform-data", { cache: "no-store" });
            if (!res.ok) return;
            const json = await res.json();
            const runs = json.pipelineRuns ?? [];
            const last = runs[0] ?? null;
            const cycle = last?.id ?? last?.run_id ?? null;
            const durationSec = durationSeconds(last?.started_at, last?.finished_at);
            const anomalies = json.anomalies ?? [];
            const actions   = json.actions ?? [];
            const pending = actions.filter((a: any) => a.status === "pending").length;

            setData({
                cycle,
                durationSec,
                openAnomalies: anomalies.length,
                l4Online: true,
                pendingActions: pending,
                lastRefreshAgo: "just now",
            });
            setLastFetch(Date.now());
        } catch {
            setData(d => ({ ...d, l4Online: false }));
        }
    };

    useEffect(() => {
        refresh();
        const id = setInterval(refresh, REFRESH_MS);
        return () => clearInterval(id);
    }, []);

    // Tick the "X ago" label every 15s without re-fetching
    const [, force] = useState(0);
    useEffect(() => {
        const id = setInterval(() => force(n => n + 1), 15_000);
        return () => clearInterval(id);
    }, []);

    return (
        <motion.div
            className="status-strip"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
        >
            <span className="status-strip-cell">
                <span className="material-symbols-outlined status-strip-icon">timer</span>
                <span className="status-strip-label">Cycle</span>
                <span className="status-strip-value">
                    {data.cycle !== null ? `#${data.cycle}` : "—"}
                </span>
                {data.durationSec !== null && (
                    <span className="status-strip-sub">· {data.durationSec}s</span>
                )}
            </span>

            <span className="status-strip-divider" />

            <span className="status-strip-cell">
                <span className={`material-symbols-outlined status-strip-icon ${data.openAnomalies > 0 ? "status-strip-icon-warn" : ""}`}>
                    warning
                </span>
                <span className="status-strip-label">OSS anomalies</span>
                <span className="status-strip-value">{data.openAnomalies}</span>
            </span>

            <span className="status-strip-divider" />

            <span className="status-strip-cell">
                <span className={`status-strip-dot ${data.l4Online ? "status-strip-dot-ok" : "status-strip-dot-err"}`} />
                <span className="status-strip-label">L4</span>
                <span className="status-strip-value">{data.l4Online ? "Online" : "Offline"}</span>
            </span>

            <span className="status-strip-divider" />

            <span className="status-strip-cell">
                <span className="material-symbols-outlined status-strip-icon">pending_actions</span>
                <span className="status-strip-label">Pending</span>
                <span className="status-strip-value">{data.pendingActions}</span>
            </span>

            <span className="status-strip-spacer" />

            <button className="status-strip-refresh" onClick={refresh} title="Refresh now">
                <span className="material-symbols-outlined status-strip-icon">refresh</span>
                <span className="status-strip-sub">{timeAgo(lastFetch)}</span>
            </button>
        </motion.div>
    );
}
