"use client";
import { useEffect, useRef, useState, useCallback } from 'react';
import { Bell, AlertTriangle, AlertCircle, CheckCircle2, Clock, X, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { formatTunisTime } from '../lib/time';

interface Action {
    id: string;
    title: string;
    severity: 'critical' | 'warning' | 'info';
    status: string;
    source?: string;
    created_at?: string;
}

interface PipelineRun {
    run_id: string;
    status: 'succeeded' | 'failed' | 'started';
    started_at: string;
    finished_at?: string | null;
    error_message?: string | null;
}

interface Anomaly {
    cell_id?: string;
    area?: string;
    severity?: number;
    kpi_name?: string;
}

interface NotificationItem {
    id: string;
    severity: 'critical' | 'warning' | 'info';
    title: string;
    desc: string;
    timestamp?: string;
}

const SEVERITY_ICON: Record<NotificationItem['severity'], typeof AlertTriangle> = {
    critical: AlertCircle,
    warning: AlertTriangle,
    info: Activity,
};

export default function NotificationPanel() {
    const [open, setOpen] = useState(false);
    const [items, setItems] = useState<NotificationItem[]>([]);
    const [loading, setLoading] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    const fetchNotifications = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/platform-data', { cache: 'no-store' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            const next: NotificationItem[] = [];

            // 1) Pending agent actions (critical/warning only)
            const pending: Action[] = (data.actions ?? []).filter(
                (a: Action) => a.status === 'pending' && (a.severity === 'critical' || a.severity === 'warning')
            );
            for (const a of pending.slice(0, 5)) {
                next.push({
                    id: `act-${a.id}`,
                    severity: a.severity,
                    title: a.title,
                    desc: `Pending approval${a.source ? ` · ${a.source}` : ''}`,
                    timestamp: a.created_at,
                });
            }

            // 2) Failed pipeline runs (most recent 3)
            const failed: PipelineRun[] = (data.pipelineRuns ?? []).filter(
                (r: PipelineRun) => r.status === 'failed'
            ).slice(0, 3);
            for (const r of failed) {
                next.push({
                    id: `run-${r.run_id}`,
                    severity: 'critical',
                    title: 'Pipeline run failed',
                    desc: r.error_message ? r.error_message.slice(0, 90) : `Run ${r.run_id.slice(0, 12)}…`,
                    timestamp: r.finished_at ?? r.started_at,
                });
            }

            // 3) High-severity recent anomalies (>0.85, top 5)
            const hotAnoms: Anomaly[] = (data.anomalies ?? [])
                .filter((a: Anomaly) => (a.severity ?? 0) > 0.85)
                .slice(0, 5);
            for (const a of hotAnoms) {
                next.push({
                    id: `anom-${a.cell_id}-${a.kpi_name}`,
                    severity: (a.severity ?? 0) > 0.95 ? 'critical' : 'warning',
                    title: `High severity on ${a.cell_id ?? 'cell'}`,
                    desc: `${a.kpi_name ?? 'KPI'} · severity ${(a.severity ?? 0).toFixed(2)}${a.area ? ` · ${a.area}` : ''}`,
                });
            }

            setItems(next);
        } catch (err) {
            console.error('[NotificationPanel]', err);
            setItems([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (open) fetchNotifications();
    }, [open, fetchNotifications]);

    useEffect(() => {
        if (!open) return;
        const onClick = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        };
        document.addEventListener('mousedown', onClick);
        return () => document.removeEventListener('mousedown', onClick);
    }, [open]);

    // Initial fetch for unread count
    useEffect(() => {
        fetchNotifications();
        const id = setInterval(fetchNotifications, 60000);
        return () => clearInterval(id);
    }, [fetchNotifications]);

    const unreadCount = items.length;

    return (
        <div ref={ref} style={{ position: 'relative' }}>
            <button
                className="top-header-icon-btn"
                title="Notifications"
                onClick={() => setOpen((v) => !v)}
                aria-expanded={open}
                aria-haspopup="true"
            >
                <Bell size={17} strokeWidth={2.2} />
                {unreadCount > 0 && (
                    <span className="top-header-notification-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
                )}
            </button>

            <AnimatePresence>
                {open && (
                    <motion.div
                        className="notification-panel"
                        initial={{ opacity: 0, y: -6, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -4, scale: 0.98 }}
                        transition={{ duration: 0.15 }}
                    >
                        <div className="notification-panel-header">
                            <div className="notification-panel-title">
                                <Bell size={14} strokeWidth={2.4} /> Notifications
                            </div>
                            <button className="notification-panel-close" onClick={() => setOpen(false)} aria-label="Close">
                                <X size={14} strokeWidth={2.4} />
                            </button>
                        </div>

                        <div className="notification-panel-body">
                            {loading && items.length === 0 ? (
                                <div className="notification-panel-empty">
                                    <Clock size={20} strokeWidth={1.6} />
                                    <span>Loading…</span>
                                </div>
                            ) : items.length === 0 ? (
                                <div className="notification-panel-empty">
                                    <CheckCircle2 size={22} strokeWidth={1.6} />
                                    <span>All clear — no alerts</span>
                                </div>
                            ) : (
                                items.map((n) => {
                                    const Icon = SEVERITY_ICON[n.severity];
                                    return (
                                        <div key={n.id} className={`notification-item notification-item-${n.severity}`}>
                                            <div className="notification-item-icon">
                                                <Icon size={15} strokeWidth={2.2} />
                                            </div>
                                            <div className="notification-item-body">
                                                <div className="notification-item-title">{n.title}</div>
                                                <div className="notification-item-desc">{n.desc}</div>
                                                {n.timestamp && (
                                                    <div className="notification-item-ts">
                                                        {formatTunisTime(n.timestamp)}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>

                        <div className="notification-panel-footer">
                            <a href="/l4-agent" className="notification-panel-link">View all in L4 Agent →</a>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
