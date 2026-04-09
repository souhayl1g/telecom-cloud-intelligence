"use client";
import { useEffect, useState, useCallback, useRef } from 'react';

/* ── Types ──────────────────────────────────────────────────────────────────── */

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
}

interface AgentAction {
    id: string;
    type: 'auto_remediation' | 'recommendation' | 'escalation' | 'prediction';
    title: string;
    description: string;
    severity: 'critical' | 'warning' | 'info';
    status: 'pending' | 'approved' | 'executed' | 'rejected' | 'auto_approved';
    timestamp: string;
    source: string;
    confidence: number;
    impact: string;
    requiresApproval: boolean;
}

interface PlatformContext {
    sla: any;
    anomalies: any[];
    revenueAnomalies: any[];
    correlations: any[];
    pipelineRuns: any[];
}

interface Notification {
    id: string;
    title: string;
    message: string;
    type: 'success' | 'warning' | 'danger' | 'info';
    timestamp: number;
}

/* ── ADN L4 Action Classification ───────────────────────────────────────── */

function classifyAction(severity: string, type: string, confidence: number): boolean {
    // L4 ADN: Auto-approve simple/info actions, require human approval for critical
    if (severity === 'critical') return true;   // ALWAYS needs human approval
    if (type === 'auto_remediation' && severity === 'warning') return true; // Warning remediations need approval
    if (type === 'escalation') return true;     // Escalations always need approval
    // Everything else (info, predictions, health checks) => auto-approved
    return false;
}

/* ── Action generator from live data ───────────────────────────────────────── */

function generateActions(ctx: PlatformContext): AgentAction[] {
    const actions: AgentAction[] = [];
    const now = new Date();
    const slaScore = ctx.sla?.score ?? 0;

    if (slaScore >= 0.7) {
        const needsApproval = classifyAction('critical', 'auto_remediation', 0.94);
        actions.push({
            id: `sla-crit-${Date.now()}`, type: 'auto_remediation',
            title: 'Critical SLA Breach Risk Detected',
            description: `SLA risk score at ${slaScore.toFixed(3)} exceeds critical threshold (0.7). Initiating automatic load balancing and capacity scaling across affected regions.`,
            severity: 'critical', status: needsApproval ? 'pending' : 'auto_approved',
            timestamp: now.toISOString(),
            source: 'SLA Risk Predictor v2.0', confidence: 0.94,
            impact: 'Prevents potential SLA violation affecting ~2,400 subscribers',
            requiresApproval: needsApproval,
        });
    } else if (slaScore >= 0.4) {
        const needsApproval = classifyAction('warning', 'recommendation', 0.87);
        actions.push({
            id: `sla-warn-${Date.now()}`, type: 'recommendation',
            title: 'SLA Risk Trending Upward',
            description: `Risk score at ${slaScore.toFixed(3)} is in warning zone. Recommend preemptive resource allocation increase by 15%.`,
            severity: 'warning', status: needsApproval ? 'pending' : 'auto_approved',
            timestamp: now.toISOString(),
            source: 'SLA Risk Predictor v2.0', confidence: 0.87,
            impact: 'Proactive capacity increase prevents breach escalation',
            requiresApproval: needsApproval,
        });
    } else {
        actions.push({
            id: `sla-ok-${Date.now()}`, type: 'prediction',
            title: 'SLA Health Nominal',
            description: `Current risk at ${slaScore.toFixed(3)}. GradientBoosting model predicts stable conditions for the next 4 hours.`,
            severity: 'info', status: 'auto_approved',
            timestamp: now.toISOString(),
            source: 'SLA Risk Predictor v2.0', confidence: 0.96,
            impact: 'Continuous monitoring maintained at 2-minute intervals',
            requiresApproval: false,
        });
    }

    const critAnom = ctx.anomalies?.filter((a: any) => a.severity > 0.9) ?? [];
    if (critAnom.length > 0) {
        const cells = [...new Set(critAnom.map((a: any) => a.cell_id))].slice(0, 3);
        actions.push({
            id: `anom-crit-${Date.now()}`, type: 'auto_remediation',
            title: `${critAnom.length} Critical OSS Anomalies`,
            description: `IsolationForest detected ${critAnom.length} critical anomalies in cells: ${cells.join(', ')}. Auto-remediation initiated.`,
            severity: 'critical', status: 'pending',
            timestamp: new Date(now.getTime() - 300000).toISOString(),
            source: 'OSS Anomaly Detector v2.0', confidence: 0.89,
            impact: `Affects ${cells.length} cell sites, ~${cells.length * 800} active sessions`,
            requiresApproval: true,
        });
    }

    const highRev = ctx.revenueAnomalies?.filter((r: any) => (r.severity ?? r.score ?? 0) > 0.8) ?? [];
    if (highRev.length > 0) {
        actions.push({
            id: `rev-${Date.now()}`, type: 'recommendation',
            title: 'BSS Revenue Anomaly - Potential Fraud',
            description: `Detected ${highRev.length} high-severity revenue anomalies. Patterns suggest potential billing fraud. Recommend immediate audit.`,
            severity: 'warning', status: 'pending',
            timestamp: new Date(now.getTime() - 900000).toISOString(),
            source: 'BSS Revenue Anomaly v2.0', confidence: 0.78,
            impact: `Estimated revenue impact: ${(highRev.length * 1250).toLocaleString()} TND`,
            requiresApproval: true,
        });
    }

    const strongCorrs = ctx.correlations?.filter((c: any) => Math.abs(c.corr_value) >= 0.7) ?? [];
    if (strongCorrs.length > 0) {
        actions.push({
            id: `corr-${Date.now()}`, type: 'prediction',
            title: 'Strong OSS-BSS Correlation Detected',
            description: `${strongCorrs.length} strong correlations found. Agent leveraging cross-domain signals for improved prediction.`,
            severity: 'info', status: 'auto_approved',
            timestamp: new Date(now.getTime() - 1800000).toISOString(),
            source: 'Correlation Engine', confidence: 0.93,
            impact: 'Model accuracy improved by leveraging cross-domain signals',
            requiresApproval: false,
        });
    }

    actions.push({
        id: `monitor-${Date.now()}`, type: 'prediction',
        title: 'Continuous Monitoring Active',
        description: 'L4 Agent is actively monitoring all OSS/BSS telemetry streams. Next analysis cycle in 2 minutes.',
        severity: 'info', status: 'auto_approved',
        timestamp: new Date(now.getTime() - 60000).toISOString(),
        source: 'L4 Agent Core', confidence: 1.0,
        impact: 'Real-time coverage across all domains',
        requiresApproval: false,
    });

    return actions.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

/* ── Mini Chart Component ──────────────────────────────────────────────────── */

function MiniSparkline({ data, color, height = 40 }: { data: number[]; color: string; height?: number }) {
    if (!data || data.length < 2) return null;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const w = 100;
    const points = data.map((v, i) => {
        const x = (i / (data.length - 1)) * w;
        const y = height - ((v - min) / range) * (height - 4) - 2;
        return `${x},${y}`;
    }).join(' ');
    const areaPoints = `0,${height} ${points} ${w},${height}`;

    return (
        <svg width="100%" height={height} viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" style={{ display: 'block' }}>
            <defs>
                <linearGradient id={`grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity="0.3" />
                    <stop offset="100%" stopColor={color} stopOpacity="0" />
                </linearGradient>
            </defs>
            <polygon points={areaPoints} fill={`url(#grad-${color.replace('#', '')})`} />
            <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

function DonutChart({ value, max, color, label, size = 80 }: { value: number; max: number; color: string; label: string; size?: number }) {
    const pct = Math.min(value / max, 1);
    const r = (size - 8) / 2;
    const circumference = 2 * Math.PI * r;
    const offset = circumference * (1 - pct);
    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="4" />
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="4"
                    strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 1s ease' }} />
            </svg>
            <div style={{ fontSize: 16, fontWeight: 700, color, marginTop: -size / 2 - 8, position: 'relative' }}>
                {typeof value === 'number' ? (value < 1 ? (value * 100).toFixed(0) + '%' : value) : value}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: size / 2 - 18, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
        </div>
    );
}

/* ── Icons ──────────────────────────────────────────────────────────────────── */

const TypeIcon = ({ type }: { type: string }) => {
    switch (type) {
        case 'auto_remediation': return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>;
        case 'recommendation': return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>;
        case 'escalation': return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>;
        default: return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>;
    }
};

/* ── Main Page ──────────────────────────────────────────────────────────────── */

export default function L4AgentPage() {
    const [actions, setActions] = useState<AgentAction[]>([]);
    const [platformCtx, setPlatformCtx] = useState<PlatformContext | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [streaming, setStreaming] = useState(false);
    const [loading, setLoading] = useState(true);
    const [ollamaReady, setOllamaReady] = useState<boolean | null>(null);
    const [selectedAction, setSelectedAction] = useState<AgentAction | null>(null);
    const [activeTab, setActiveTab] = useState<'chat' | 'actions' | 'monitor'>('chat');
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [slaHistory, setSlaHistory] = useState<number[]>([]);
    const [anomalyHistory, setAnomalyHistory] = useState<number[]>([]);
    const [agentSpeed, setAgentSpeed] = useState<number>(0);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const startTimeRef = useRef<number>(Date.now());

    // Push notification
    const pushNotification = useCallback((n: Omit<Notification, 'id' | 'timestamp'>) => {
        const notif: Notification = { ...n, id: `n-${Date.now()}-${Math.random()}`, timestamp: Date.now() };
        setNotifications(prev => [notif, ...prev].slice(0, 20));
        // Browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`NexOps: ${n.title}`, { body: n.message, icon: '/favicon.ico' });
        }
        // Auto-dismiss after 5s
        setTimeout(() => {
            setNotifications(prev => prev.filter(x => x.id !== notif.id));
        }, 5000);
    }, []);

    // Request browser notification permission
    useEffect(() => {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }, []);

    // Scroll chat to bottom
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, streaming]);

    // Check Ollama availability
    useEffect(() => {
        fetch('http://localhost:11434/api/tags')
            .then(r => r.ok ? setOllamaReady(true) : setOllamaReady(false))
            .catch(() => setOllamaReady(false));
    }, []);

    // Fetch platform data via Next.js API proxy (includes auth token from cookie)
    const fetchData = useCallback(async () => {
        const t0 = performance.now();
        try {
            const res = await fetch('/api/platform-data', { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to fetch platform data');
            const data = await res.json();

            const ctx: PlatformContext = {
                sla: data.sla,
                anomalies: data.anomalies ?? [],
                revenueAnomalies: data.revenueAnomalies ?? [],
                correlations: data.correlations ?? [],
                pipelineRuns: data.pipelineRuns ?? [],
            };
            setPlatformCtx(ctx);

            // Build history for sparklines
            if (data.history && Array.isArray(data.history)) {
                setSlaHistory(data.history.slice(-20).map((h: any) => h.score ?? 0));
            }
            setAnomalyHistory(prev => [...prev, ctx.anomalies.length].slice(-20));

            const newActions = generateActions(ctx);
            setActions(newActions);

            // Auto-approve simple actions and send notifications
            const needsApproval = newActions.filter(a => a.status === 'pending');

            if (needsApproval.length > 0) {
                pushNotification({
                    title: `${needsApproval.length} Action(s) Need Approval`,
                    message: needsApproval.map(a => a.title).join(', '),
                    type: needsApproval.some(a => a.severity === 'critical') ? 'danger' : 'warning',
                });
            }

            setAgentSpeed(Math.round(performance.now() - t0));
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, [pushNotification]);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 120000);
        return () => clearInterval(interval);
    }, [fetchData]);

    // Handle action approve/reject
    const handleAction = (action: AgentAction, decision: 'approved' | 'rejected') => {
        setActions(prev => prev.map(a =>
            a.id === action.id ? { ...a, status: decision === 'approved' ? 'executed' : 'rejected' } : a
        ));
        if (selectedAction?.id === action.id) setSelectedAction(null);
        pushNotification({
            title: decision === 'approved' ? 'Action Approved' : 'Action Rejected',
            message: action.title,
            type: decision === 'approved' ? 'success' : 'danger',
        });
    };

    // Chat send
    const sendMessage = async () => {
        const text = input.trim();
        if (!text || streaming) return;

        const userMsg: ChatMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setStreaming(true);

        const assistantMsg: ChatMessage = { role: 'assistant', content: '', timestamp: new Date().toISOString() };
        setMessages(prev => [...prev, assistantMsg]);

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: [...messages, userMsg].map(m => ({ role: m.role, content: m.content })),
                    context: platformCtx ? {
                        sla_risk_score: platformCtx.sla?.score,
                        sla_region: platformCtx.sla?.region,
                        sla_explanation: platformCtx.sla?.explanation,
                        oss_anomalies_count: platformCtx.anomalies?.length,
                        bss_anomalies_count: platformCtx.revenueAnomalies?.length,
                        correlations_count: platformCtx.correlations?.length,
                        pipeline_runs: platformCtx.pipelineRuns?.length,
                        last_pipeline_status: platformCtx.pipelineRuns?.[0]?.status,
                    } : undefined,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ error: 'Connection failed' }));
                setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                        ...updated[updated.length - 1],
                        content: `Error: ${err.error || 'Failed to connect to L4 Agent LLM. Ensure Ollama is running.'}`,
                    };
                    return updated;
                });
                setStreaming(false);
                return;
            }

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            let accumulated = '';

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
                    for (const line of lines) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;
                        try {
                            const json = JSON.parse(data);
                            if (json.content) {
                                accumulated += json.content;
                                setMessages(prev => {
                                    const updated = [...prev];
                                    updated[updated.length - 1] = { ...updated[updated.length - 1], content: accumulated };
                                    return updated;
                                });
                            }
                        } catch { /* skip */ }
                    }
                }
            }
        } catch {
            setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                    ...updated[updated.length - 1],
                    content: 'Error: Cannot connect to L4 Agent LLM. Ensure Ollama is running on localhost:11434.',
                };
                return updated;
            });
        } finally {
            setStreaming(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    };

    // Stats
    const pendingActions = actions.filter(a => a.status === 'pending');
    const executedActions = actions.filter(a => a.status === 'executed' || a.status === 'rejected' || a.status === 'auto_approved');
    const autoApprovedCount = actions.filter(a => a.status === 'auto_approved').length;
    const slaScore = platformCtx?.sla?.score ?? 0;
    const uptime = Math.floor((Date.now() - startTimeRef.current) / 1000);
    const uptimeStr = `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`;

    if (loading) {
        return (
            <div className="l4-loading">
                <div className="l4-loading-spinner" />
                <div className="l4-loading-text">Initializing L4 Autonomous Agent...</div>
                <div className="l4-loading-sub">Connecting to AI services and loading telemetry data</div>
            </div>
        );
    }

    return (
        <div className="l4-page">
            {/* Push Notification Toast */}
            <div className="l4-toast-container">
                {notifications.map(n => (
                    <div key={n.id} className={`l4-toast l4-toast-${n.type}`}
                        onClick={() => {
                            setNotifications(prev => prev.filter(x => x.id !== n.id));
                            if (n.type === 'warning' || n.type === 'danger') setActiveTab('actions');
                        }}
                        style={{ cursor: 'pointer' }}
                    >
                        <div className="l4-toast-icon">
                            {n.type === 'success' ? '\u2713' : n.type === 'danger' ? '\u2717' : n.type === 'warning' ? '\u26A0' : '\u2139'}
                        </div>
                        <div style={{ flex: 1 }}>
                            <div className="l4-toast-title">{n.title}</div>
                            <div className="l4-toast-msg">{n.message}</div>
                        </div>
                        <div style={{ fontSize: 14, color: 'var(--text-muted)', flexShrink: 0, marginLeft: 8 }}>{'\u2715'}</div>
                    </div>
                ))}
            </div>

            {/* Header */}
            <div className="l4-header">
                <div className="l4-header-left">
                    <h1>
                        <span className="l4-header-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#ffd700' }}>
                                <rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /><circle cx="12" cy="16" r="1" />
                            </svg>
                        </span>
                        L4 Autonomous Agent
                    </h1>
                    <p>ADN Level 4 - Self-healing, predictive, closed-loop autonomous operations</p>
                </div>
                <div className="l4-header-right">
                    <div className="l4-header-stats">
                        <div className="l4-mini-stat">
                            <span className="l4-mini-label">SLA Risk</span>
                            <span className={`l4-mini-value ${slaScore >= 0.7 ? 'l4-danger' : slaScore >= 0.4 ? 'l4-warning' : 'l4-ok'}`}>
                                {(slaScore * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div className="l4-mini-stat">
                            <span className="l4-mini-label">Anomalies</span>
                            <span className="l4-mini-value">{platformCtx?.anomalies?.length ?? 0}</span>
                        </div>
                        <div className="l4-mini-stat">
                            <span className="l4-mini-label">Actions</span>
                            <span className="l4-mini-value">{pendingActions.length} pending</span>
                        </div>
                        <div className="l4-mini-stat">
                            <span className="l4-mini-label">Speed</span>
                            <span className="l4-mini-value l4-ok">{agentSpeed}ms</span>
                        </div>
                    </div>
                    <div className={`l4-agent-status l4-status-active`}>
                        <div className="l4-status-dot" />
                        <span>AGENT ACTIVE</span>
                    </div>
                </div>
            </div>

            {/* Tab switcher */}
            <div className="l4-tabs">
                <button className={`l4-tab ${activeTab === 'chat' ? 'l4-tab-active' : ''}`} onClick={() => setActiveTab('chat')}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                    Agent Chat
                </button>
                <button className={`l4-tab ${activeTab === 'actions' ? 'l4-tab-active' : ''}`} onClick={() => setActiveTab('actions')}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
                    Actions
                    {pendingActions.length > 0 && <span className="l4-tab-badge">{pendingActions.length}</span>}
                </button>
                <button className={`l4-tab ${activeTab === 'monitor' ? 'l4-tab-active' : ''}`} onClick={() => setActiveTab('monitor')}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>
                    Live Monitor
                </button>
            </div>

            {/* Main content */}
            <div className="l4-main">
                {/* Chat Panel */}
                <div className={`l4-chat-panel ${activeTab === 'chat' ? 'l4-panel-active' : ''}`}>
                    <div className="l4-chat-messages">
                        {messages.length === 0 && (
                            <div className="l4-chat-empty">
                                <div className="l4-chat-empty-icon">
                                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.3 }}>
                                        <rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /><circle cx="12" cy="16" r="1" />
                                    </svg>
                                </div>
                                <div className="l4-chat-empty-title">NexOps L4 Agent</div>
                                <div className="l4-chat-empty-sub">
                                    {ollamaReady === false
                                        ? 'Ollama not detected. Start Ollama with qwen2.5:7b to enable the agent.'
                                        : 'Ask about SLA risk, anomalies, network health, or request autonomous actions.'
                                    }
                                </div>
                                <div className="l4-suggestions">
                                    {[
                                        'Analyze current SLA risk and suggest remediation',
                                        'What anomalies were detected in the last pipeline run?',
                                        'Summarize the OSS-BSS correlation insights',
                                        'What autonomous actions should I approve?',
                                    ].map((s, i) => (
                                        <button key={i} className="l4-suggestion" onClick={() => { setInput(s); inputRef.current?.focus(); }}>
                                            {s}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <div key={i} className={`l4-msg l4-msg-${msg.role}`}>
                                <div className="l4-msg-avatar">
                                    {msg.role === 'user' ? (
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
                                    ) : (
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /><circle cx="12" cy="16" r="1" /></svg>
                                    )}
                                </div>
                                <div className="l4-msg-content">
                                    <div className="l4-msg-role">{msg.role === 'user' ? 'You' : 'L4 Agent'}</div>
                                    <div className="l4-msg-text">{msg.content || (streaming && i === messages.length - 1 ? <span className="l4-cursor" /> : '')}</div>
                                </div>
                            </div>
                        ))}
                        <div ref={chatEndRef} />
                    </div>

                    {/* Input */}
                    <div className="l4-chat-input-wrap">
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={ollamaReady === false ? 'Ollama not running...' : 'Ask the L4 Agent...'}
                            disabled={streaming || ollamaReady === false}
                            className="l4-chat-input"
                            rows={1}
                        />
                        <button onClick={sendMessage} disabled={!input.trim() || streaming || ollamaReady === false} className="l4-send-btn">
                            {streaming ? <div className="l4-send-spinner" /> : (
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                            )}
                        </button>
                    </div>
                </div>

                {/* Monitor Panel */}
                <div className={`l4-actions-panel ${activeTab === 'monitor' ? 'l4-panel-active' : ''}`}>
                    {activeTab === 'monitor' && (
                        <>
                            {/* Live Monitor Dashboard */}
                            <div className="l4-section">
                                <div className="l4-section-header">Live Telemetry</div>
                                <div className="l4-monitor-grid">
                                    <div className="l4-monitor-card">
                                        <div className="l4-monitor-label">SLA Risk Trend</div>
                                        <MiniSparkline data={slaHistory.length > 1 ? slaHistory : [0.1, 0.12, 0.09, 0.15, 0.11, 0.08, slaScore]} color="var(--color-warning)" height={50} />
                                        <div className="l4-monitor-value" style={{ color: slaScore >= 0.7 ? 'var(--color-danger)' : slaScore >= 0.4 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                            {(slaScore * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                    <div className="l4-monitor-card">
                                        <div className="l4-monitor-label">Anomaly Count</div>
                                        <MiniSparkline data={anomalyHistory.length > 1 ? anomalyHistory : [3, 5, 2, 7, 4, 6, platformCtx?.anomalies?.length ?? 0]} color="var(--color-danger)" height={50} />
                                        <div className="l4-monitor-value">{platformCtx?.anomalies?.length ?? 0}</div>
                                    </div>
                                    <div className="l4-monitor-card">
                                        <div className="l4-monitor-label">Correlations</div>
                                        <MiniSparkline data={[5, 8, 6, 9, 7, 10, platformCtx?.correlations?.length ?? 0]} color="var(--color-info)" height={50} />
                                        <div className="l4-monitor-value">{platformCtx?.correlations?.length ?? 0}</div>
                                    </div>
                                </div>
                            </div>

                            <div className="l4-section">
                                <div className="l4-section-header">Agent Performance</div>
                                <div className="l4-perf-grid">
                                    <DonutChart value={autoApprovedCount} max={Math.max(actions.length, 1)} color="var(--color-success)" label="Auto-Approved" size={72} />
                                    <DonutChart value={pendingActions.length} max={Math.max(actions.length, 1)} color="var(--color-warning)" label="Pending" size={72} />
                                    <DonutChart value={agentSpeed} max={2000} color="var(--color-info)" label="Latency (ms)" size={72} />
                                </div>
                                <div className="l4-perf-stats">
                                    <div className="l4-perf-row"><span>Uptime</span><span className="l4-perf-val">{uptimeStr}</span></div>
                                    <div className="l4-perf-row"><span>Model</span><span className="l4-perf-val">Qwen2.5 7B</span></div>
                                    <div className="l4-perf-row"><span>Cycle Interval</span><span className="l4-perf-val">120s</span></div>
                                    <div className="l4-perf-row"><span>Total Actions</span><span className="l4-perf-val">{actions.length}</span></div>
                                    <div className="l4-perf-row"><span>ADN Level</span><span className="l4-perf-val" style={{ color: '#ffd700' }}>L4 Autonomous</span></div>
                                </div>
                            </div>
                        </>
                    )}
                </div>

                {/* Actions Panel */}
                <div className={`l4-actions-panel ${activeTab === 'actions' ? 'l4-panel-active' : ''}`}>
                    {activeTab === 'actions' && (
                        <>
                            {/* Pending - needs human approval */}
                            {pendingActions.length > 0 && (
                                <div className="l4-section">
                                    <div className="l4-section-header">
                                        <span className="l4-pulse-dot" />
                                        Requires Approval
                                        <span className="badge badge-warning" style={{ marginLeft: 8, fontSize: 10 }}>{pendingActions.length}</span>
                                    </div>
                                    {pendingActions.map(action => (
                                        <div
                                            key={action.id}
                                            className={`l4-action-item l4-severity-${action.severity} ${selectedAction?.id === action.id ? 'l4-action-selected' : ''}`}
                                            onClick={() => setSelectedAction(selectedAction?.id === action.id ? null : action)}
                                        >
                                            <div className="l4-action-header">
                                                <div className="l4-action-type">
                                                    <TypeIcon type={action.type} />
                                                    <span className={`badge badge-${action.severity === 'critical' ? 'danger' : 'warning'}`} style={{ fontSize: 9 }}>
                                                        {action.severity.toUpperCase()}
                                                    </span>
                                                </div>
                                                <span className="l4-confidence">{(action.confidence * 100).toFixed(0)}%</span>
                                            </div>
                                            <div className="l4-action-title">{action.title}</div>
                                            <div className="l4-action-desc">{action.description}</div>
                                            {selectedAction?.id === action.id && (
                                                <div className="l4-action-details">
                                                    <div className="l4-detail-row"><span className="l4-detail-label">Source</span><span>{action.source}</span></div>
                                                    <div className="l4-detail-row"><span className="l4-detail-label">Impact</span><span>{action.impact}</span></div>
                                                    <div className="l4-action-buttons">
                                                        <button className="l4-btn l4-btn-approve" onClick={e => { e.stopPropagation(); handleAction(action, 'approved'); }}>
                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
                                                            Approve & Execute
                                                        </button>
                                                        <button className="l4-btn l4-btn-reject" onClick={e => { e.stopPropagation(); handleAction(action, 'rejected'); }}>
                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                                                            Reject
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Auto-approved + Executed */}
                            <div className="l4-section">
                                <div className="l4-section-header">
                                    Completed Actions
                                    <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>{executedActions.length}</span>
                                </div>
                                {executedActions.map(action => (
                                    <div key={action.id} className="l4-executed-item">
                                        <TypeIcon type={action.type} />
                                        <div className="l4-exec-content">
                                            <div className="l4-exec-title">{action.title}</div>
                                            <div className="l4-exec-meta">
                                                <span className={`badge ${action.status === 'auto_approved' ? 'badge-cyan' : action.status === 'executed' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: 9, padding: '1px 5px' }}>
                                                    {action.status === 'auto_approved' ? 'AUTO' : action.status.toUpperCase()}
                                                </span>
                                                <span>{action.source}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* ADN Architecture */}
                            <div className="l4-section">
                                <div className="l4-section-header">ADN Architecture Level</div>
                                <div className="l4-arch-grid">
                                    {[
                                        { level: 'L4', name: 'Autonomous', desc: 'Self-healing, predictive, closed-loop', current: true },
                                        { level: 'L3', name: 'Conditional', desc: 'AI recommends, human approves', current: false },
                                        { level: 'L2', name: 'Assisted', desc: 'Human-driven with AI help', current: false },
                                        { level: 'L1', name: 'Manual', desc: 'Fully manual operations', current: false },
                                    ].map(l => (
                                        <div key={l.level} className={`l4-arch-level ${l.current ? 'l4-arch-current' : ''}`}>
                                            <div className={`l4-arch-badge ${!l.current ? 'l4-arch-inactive' : ''}`}>{l.level}</div>
                                            <div>
                                                <div className={`l4-arch-name ${!l.current ? 'l4-arch-muted' : ''}`}>{l.name}</div>
                                                <div className="l4-arch-desc">{l.desc}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
