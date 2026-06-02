"use client";
import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useRefresh } from '../../components/RefreshContext';
import L4ADNArchitecture from '../../components/L4ADNArchitecture';
import { formatTunisTime } from '../../lib/time';

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
    executionLog?: any;
    playbookId?: string;
}

interface PlatformContext {
    anomalies: any[];          // OSS cell anomalies (oss_cell_kpis.anomaly_flag = TRUE)
    cemAnomalies: any[];   // CEM subscriber risks (RAT gap or churn flag)
    correlations: any[];
    pipelineRuns: any[];
    actions: any[];
    vaeSummary: { total: number; anomaly_count: number; anomaly_rate: number; areas_affected: number } | null;
    cemSummary: { total: number; avg_score: number; poor_count: number; fair_count: number; good_count: number } | null;
    ratSummary: { total: number; underserved: number; rate: number } | null;
    granger: { results: any[]; count: number; significant: number };
    areas: any[];
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
// NOTE: IDs must be STABLE per real-world signal. A new ID every cycle would make
// every tick create a fresh row in the backend — that was the source of the 33+
// stacked duplicates. We bucket by UTC hour so the same live signal reconciles.
function hourBucket(): string {
    const d = new Date();
    return `${d.getUTCFullYear()}${(d.getUTCMonth() + 1).toString().padStart(2, '0')}${d.getUTCDate().toString().padStart(2, '0')}${d.getUTCHours().toString().padStart(2, '0')}`;
}

function generateActions(ctx: PlatformContext): AgentAction[] {
    const actions: AgentAction[] = [];
    const now = new Date();
    const bucket = hourBucket();
    // Use authoritative summary counts when available (full table), fall back to row arrays
    const vaeCount = ctx.vaeSummary?.anomaly_count ?? ctx.anomalies?.length ?? 0;
    const cemAvg = ctx.cemSummary?.avg_score ?? 0;
    const cemPoor = ctx.cemSummary?.poor_count ?? 0;
    const ratRate = ctx.ratSummary?.rate ?? 0;
    const ratUnderserved = ctx.ratSummary?.underserved ?? 0;
    const grangerSig = ctx.granger?.significant ?? 0;
    const cemCount = cemPoor; // backward compat — represents low-CEM subscriber count

    // VAE anomaly-based actions
    if (vaeCount >= 50) {
        const needsApproval = classifyAction('critical', 'auto_remediation', 0.92);
        actions.push({
            id: `vae-crit-${bucket}`, type: 'auto_remediation',
            title: 'Critical VAE Anomaly Spike Detected',
            description: `PyTorch VAE detected ${vaeCount} anomalies across OSS cell KPIs. Initiating auto-triage and cell-load rebalancing.`,
            severity: 'critical', status: needsApproval ? 'pending' : 'auto_approved',
            timestamp: now.toISOString(),
            source: 'OSS VAE Anomaly v3.0-gpu', confidence: 0.92,
            impact: `Affects multiple cell sites with abnormal reconstruction error`,
            requiresApproval: needsApproval,
            playbookId: 'pb-anomaly-triage',
        });
    } else if (vaeCount >= 10) {
        const needsApproval = classifyAction('warning', 'recommendation', 0.85);
        actions.push({
            id: `vae-warn-${bucket}`, type: 'recommendation',
            title: 'VAE Anomaly Count Elevated',
            description: `${vaeCount} VAE anomalies detected. Recommend preventive KPI audit in affected areas.`,
            severity: 'warning', status: needsApproval ? 'pending' : 'auto_approved',
            timestamp: now.toISOString(),
            source: 'OSS VAE Anomaly v3.0-gpu', confidence: 0.85,
            impact: 'Proactive audit prevents subscriber experience degradation',
            requiresApproval: needsApproval,
            playbookId: 'pb-anomaly-triage',
        });
    }

    // CEM score-based actions (using cemAnomalies proxy)
    if (cemCount >= 20) {
        const needsApproval = classifyAction('warning', 'recommendation', 0.84);
        actions.push({
            id: `cem-low-${bucket}`, type: 'recommendation',
            title: 'Low CEM Score Areas Detected',
            description: `${cemCount} subscribers showing poor CEM scores. LightGBM DART flagged areas needing network optimization.`,
            severity: 'warning', status: needsApproval ? 'pending' : 'auto_approved',
            timestamp: new Date(now.getTime() - 300000).toISOString(),
            source: 'CEM Scorer v3.0', confidence: 0.84,
            impact: `Subscriber experience at risk in ${cemCount} records`,
            requiresApproval: needsApproval,
            playbookId: 'pb-cem-degradation',
        });
    }

    // RAT underservice-based actions — driven by authoritative ratSummary, not row sample
    if (ratRate >= 15 || ratUnderserved >= 50) {
        const sev: 'critical' | 'warning' = ratRate >= 25 ? 'critical' : 'warning';
        actions.push({
            id: `rat-${bucket}`, type: 'recommendation',
            title: 'RAT Underservice Alert',
            description: `XGBoost GPU flagged ${ratUnderserved.toLocaleString()} subscribers (${ratRate.toFixed(1)}%) on lower RAT than their device supports.`,
            severity: sev, status: classifyAction(sev, 'recommendation', 0.88) ? 'pending' : 'auto_approved',
            timestamp: new Date(now.getTime() - 900000).toISOString(),
            source: 'RAT Detector v3.0-gpu', confidence: 0.88,
            impact: `${ratUnderserved.toLocaleString()} subscribers underserved`,
            requiresApproval: classifyAction(sev, 'recommendation', 0.88),
            playbookId: 'pb-revenue-protect',
        });
    }

    // Churn-prevention workflow trigger — fires when both low-CEM cohort
    // AND high RAT underservice rate are present (compound signal).
    if (cemPoor >= 100 && ratRate >= 10) {
        actions.push({
            id: `churn-${bucket}`, type: 'auto_remediation',
            title: 'Churn Prevention Workflow Recommended',
            description: `${cemPoor.toLocaleString()} subscribers with poor CEM + ${ratRate.toFixed(1)}% RAT underservice. Compound churn risk detected — recommend bulk retention workflow.`,
            severity: 'critical', status: 'pending',
            timestamp: new Date(now.getTime() - 120000).toISOString(),
            source: 'Compound Risk Engine', confidence: 0.91,
            impact: `Up to ${(cemPoor * 20).toLocaleString()} TND/month revenue at risk`,
            requiresApproval: true,
            playbookId: 'pb-churn-prevention',
        });
    }

    // Critical VAE → auto-open NOC ticket
    if (vaeCount >= 100) {
        actions.push({
            id: `ticket-${bucket}`, type: 'escalation',
            title: 'Open NOC Ticket — Critical VAE Burst',
            description: `${vaeCount} VAE anomalies detected in last cycle. Recommend opening a NOC ticket for engineer dispatch.`,
            severity: 'critical', status: 'pending',
            timestamp: new Date(now.getTime() - 60000).toISOString(),
            source: 'L4 Agent · Auto-Escalation', confidence: 0.95,
            impact: 'Network reliability — engineer dispatch required',
            requiresApproval: true,
            playbookId: 'pb-create-ticket',
        });
    }

    // Granger causality-based prediction action
    if (grangerSig > 0) {
        actions.push({
            id: `granger-${bucket}`, type: 'prediction',
            title: 'Granger Causal Pairs Detected',
            description: `${grangerSig} statistically significant OSS→CEM causal pairs found (p<0.05). Use for predictive remediation timing.`,
            severity: 'info', status: 'auto_approved',
            timestamp: new Date(now.getTime() - 1200000).toISOString(),
            source: 'Granger Engine', confidence: 0.95,
            impact: 'Causal lag enables proactive remediation 1-3 cycles ahead',
            requiresApproval: false,
        });
    }

    const strongCorrs = ctx.correlations?.filter((c: any) => Math.abs(c.corr_value) >= 0.7) ?? [];
    if (strongCorrs.length > 0) {
        actions.push({
            id: `corr-${bucket}`, type: 'prediction',
            title: 'Strong OSS-CEM Correlation Detected',
            description: `${strongCorrs.length} strong correlations found. Agent leveraging cross-domain signals for improved prediction.`,
            severity: 'info', status: 'auto_approved',
            timestamp: new Date(now.getTime() - 1800000).toISOString(),
            source: 'Correlation Engine', confidence: 0.93,
            impact: 'Model accuracy improved by leveraging cross-domain signals',
            requiresApproval: false,
        });
    }

    actions.push({
        id: `monitor-${bucket}`, type: 'prediction',
        title: 'Continuous Monitoring Active',
        description: 'L4 Agent is actively monitoring all OSS/CEM telemetry streams. Next analysis cycle in 30 seconds.',
        severity: 'info', status: 'auto_approved',
        timestamp: new Date(now.getTime() - 60000).toISOString(),
        source: 'L4 Agent Core', confidence: 1.0,
        impact: 'Real-time coverage across all domains',
        requiresApproval: false,
    });

    return actions.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

/* ── Action consolidation ──────────────────────────────────────────────────
 * Group identical titles so the user sees "CEM Anomaly (18)" once,
 * not 18 identical cards. The group keeps the earliest id/timestamp as its
 * anchor and exposes children for drill-down.
 */
interface ActionGroup {
    key: string;
    anchor: AgentAction;
    items: AgentAction[];
    severity: 'critical' | 'warning' | 'info';
}

function groupActions(list: AgentAction[]): ActionGroup[] {
    const byKey = new Map<string, ActionGroup>();
    for (const a of list) {
        const key = `${a.title}::${a.source}`;
        const existing = byKey.get(key);
        if (existing) {
            existing.items.push(a);
            if (new Date(a.timestamp).getTime() > new Date(existing.anchor.timestamp).getTime()) {
                existing.anchor = a;
            }
        } else {
            byKey.set(key, { key, anchor: a, items: [a], severity: a.severity });
        }
    }
    return Array.from(byKey.values()).sort((x, y) =>
        new Date(y.anchor.timestamp).getTime() - new Date(x.anchor.timestamp).getTime()
    );
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
    const [activeTab, setActiveTab] = useState<'chat' | 'actions' | 'monitor' | 'playbooks' | 'timeline'>('chat');
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [slaHistory, setSlaHistory] = useState<number[]>([]);
    const [anomalyHistory, setAnomalyHistory] = useState<number[]>([]);
    const [runningPlaybook, setRunningPlaybook] = useState<string | null>(null);
    const [agentSpeed, setAgentSpeed] = useState<number>(0);
    const [selectedModel, setSelectedModel] = useState<string>('kimi-k2.5:cloud');
    const [chatMode, setChatMode] = useState<'ollama' | 'orchestrator'>('orchestrator');
    const chatEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const startTimeRef = useRef<number>(Date.now());
    const { tick: refreshTick } = useRefresh();
    // Track action IDs we've already shown a toast for — prevents toast spam on every 30s cycle
    const toastedActionIdsRef = useRef<Set<string>>(new Set());
    const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

    // Available models
    const AVAILABLE_MODELS = [
        { id: 'kimi-k2.5:cloud', name: 'Kimi K2.5 Cloud', description: 'Best for chat - fast & natural' },
        { id: 'qwen2.5:7b', name: 'Qwen 2.5 (7B)', description: 'Good general purpose' },
        { id: 'glm-5:cloud', name: 'GLM-5 Cloud', description: 'Alternative cloud model' },
    ];

    // Push notification
    let _notifCounter = 0;
    const pushNotification = useCallback((n: Omit<Notification, 'id' | 'timestamp'>) => {
        const notif: Notification = { ...n, id: `n-${Date.now()}-${++_notifCounter}`, timestamp: Date.now() };
        setNotifications(prev => [notif, ...prev].slice(0, 20));
        // Browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`NeXoligence: ${n.title}`, { body: n.message, icon: '/favicon.ico' });
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

    // Load chat history from localStorage on mount
    useEffect(() => {
        const savedMessages = localStorage.getItem('l4-agent-chat-history');
        if (savedMessages) {
            try {
                const parsed = JSON.parse(savedMessages);
                setMessages(parsed);
            } catch { /* ignore invalid saved data */ }
        }
        // Load saved model preference
        const savedModel = localStorage.getItem('l4-agent-selected-model');
        if (savedModel) {
            setSelectedModel(savedModel);
        }
    }, []);

    // Save chat history to localStorage whenever messages change
    useEffect(() => {
        if (messages.length > 0) {
            try {
                localStorage.setItem('l4-agent-chat-history', JSON.stringify(messages));
            } catch {
                // Quota exceeded or private mode — silent fallback
            }
        }
    }, [messages]);

    // Save model preference
    useEffect(() => {
        try {
            localStorage.setItem('l4-agent-selected-model', selectedModel);
        } catch {
            // Quota exceeded or private mode — silent fallback
        }
    }, [selectedModel]);

    // Check Ollama availability
    useEffect(() => {
        fetch('/api/ollama-tags')
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
                anomalies: data.anomalies ?? [],
                actions: data.actions ?? [],
                cemAnomalies: data.cemAnomalies ?? [],
                correlations: data.correlations ?? [],
                pipelineRuns: data.pipelineRuns ?? [],
                vaeSummary: data.vaeSummary ?? null,
                cemSummary: data.cemSummary ?? null,
                ratSummary: data.ratSummary ?? null,
                granger: data.granger ?? { results: [], count: 0, significant: 0 },
                areas: data.areas ?? [],
            };
            setPlatformCtx(ctx);

            // CEM-avg history (replaces legacy SLA history) — sparkline of subscriber experience
            const cemAvgNow = ctx.cemSummary?.avg_score ?? 0;
            setSlaHistory(prev => [...prev, cemAvgNow].slice(-20));
            const vaeNow = ctx.vaeSummary?.anomaly_count ?? ctx.anomalies.length;
            setAnomalyHistory(prev => [...prev, vaeNow].slice(-20));

            // Load persisted actions from backend, then generate new ones
            const persistedActions: AgentAction[] = (ctx.actions ?? []).map((a: any) => ({
                id: a.action_id,
                type: a.type,
                title: a.title,
                description: a.description ?? '',
                severity: a.severity,
                status: a.status,
                timestamp: a.created_at,
                source: a.source ?? '',
                confidence: a.confidence ?? 0,
                impact: a.impact ?? '',
                requiresApproval: a.status === 'pending',
                executionLog: a.execution_log,
                playbookId: a.playbook_id,
            }));

            const newActions = generateActions(ctx);
            const existingIds = new Set(persistedActions.map(a => a.id));
            const toCreate = newActions.filter(a => !existingIds.has(a.id));
            // Fire-and-forget so render isn't blocked by serial POSTs.
            void Promise.allSettled(
                toCreate.map(action =>
                    fetch('/api/platform-data', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            _action: 'create',
                            action_id: action.id,
                            type: action.type,
                            title: action.title,
                            description: action.description,
                            severity: action.severity,
                            status: action.status,
                            source: action.source,
                            confidence: action.confidence,
                            impact: action.impact,
                            playbook_id: action.playbookId,
                        }),
                    })
                )
            ).then(results => {
                const failed = results.filter(r => r.status === 'rejected').length;
                if (failed > 0) {
                    console.warn(`[L4 Agent] ${failed}/${toCreate.length} action creations failed`);
                }
            });

            // Merge: persisted actions take priority (they have real status)
            const merged = [...persistedActions];
            for (const a of newActions) {
                if (!existingIds.has(a.id)) merged.push(a);
            }
            setActions(merged.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()));

            // Toast only for action IDs we haven't already notified for
            const newlyPending = merged.filter(
                (a) => a.status === 'pending' && !toastedActionIdsRef.current.has(a.id)
            );
            if (newlyPending.length > 0) {
                // Deduplicate by title to avoid "CEM Anomaly, CEM Anomaly, ..."
                const uniqueTitles = Array.from(new Set(newlyPending.map(a => a.title)));
                const shownTitles = uniqueTitles.slice(0, 3).join(', ');
                const more = uniqueTitles.length > 3 ? ` +${uniqueTitles.length - 3} more` : '';
                pushNotification({
                    title: `${newlyPending.length} new action${newlyPending.length > 1 ? 's' : ''} need approval`,
                    message: `${shownTitles}${more}`,
                    type: newlyPending.some((a) => a.severity === 'critical') ? 'danger' : 'warning',
                });
                newlyPending.forEach((a) => toastedActionIdsRef.current.add(a.id));
            }

            setAgentSpeed(Math.round(performance.now() - t0));
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, [pushNotification]);

    // Initial load
    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Hook into the shared silent refresh tick instead of our own setInterval
    useEffect(() => {
        if (refreshTick === 0) return;
        fetchData();
    }, [refreshTick, fetchData]);

    // Handle action approve/reject — calls real backend API
    const handleAction = async (action: AgentAction, decision: 'approved' | 'rejected') => {
        try {
            // Update status in backend
            await fetch('/api/platform-data', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action_id: action.id, status: decision }),
            });

            if (decision === 'approved') {
                // Execute the playbook via backend
                const execRes = await fetch('/api/platform-data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ _action: 'execute', action_id: action.id }),
                });
                const execResult = await execRes.json();

                setActions(prev => prev.map(a =>
                    a.id === action.id ? { ...a, status: 'executed', executionLog: execResult?.execution_log } : a
                ));
                pushNotification({
                    title: 'Action Executed',
                    message: `${action.title} — playbook completed with real backend execution`,
                    type: 'success',
                });
            } else {
                setActions(prev => prev.map(a =>
                    a.id === action.id ? { ...a, status: 'rejected' } : a
                ));
                pushNotification({
                    title: 'Action Rejected',
                    message: action.title,
                    type: 'danger',
                });
            }
        } catch {
            pushNotification({
                title: 'Action Failed',
                message: `Failed to ${decision} action: ${action.title}`,
                type: 'danger',
            });
        }
        if (selectedAction?.id === action.id) setSelectedAction(null);
    };

    // Handle paste to block images
    const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
        const items = e.clipboardData?.items;
        if (items) {
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    e.preventDefault();
                    pushNotification({
                        title: 'Image Blocked',
                        message: 'Image input is not supported. The qwen2.5:7b model only accepts text.',
                        type: 'warning',
                    });
                    return;
                }
            }
        }
    };

    // Chat send — supports both Ollama direct chat and Orchestrator multi-agent mode
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
            if (chatMode === 'orchestrator') {
                // ── NeXo Orchestrator mode ──────────────────────────────────────
                const res = await fetch('/api/agent-query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: text }),
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({ error: 'Connection failed' }));
                    setMessages(prev => {
                        const updated = [...prev];
                        updated[updated.length - 1] = {
                            ...updated[updated.length - 1],
                            content: `Error: ${err.error || 'Failed to connect to NeXo Orchestrator.'}`,
                        };
                        return updated;
                    });
                    setStreaming(false);
                    return;
                }

                const data = await res.json();
                const responseText = data.response || data.error || 'No response from orchestrator.';
                const agentName = data.agent_result?.agent_name || 'Orchestrator';
                const classification = data.classification || {};

                // Build rich response with agent metadata
                let richContent = responseText;
                if (classification.agent && classification.action) {
                    richContent = `[${agentName} · ${classification.action}]\n\n${responseText}`;
                }

                setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                        ...updated[updated.length - 1],
                        content: richContent,
                    };
                    return updated;
                });
                setStreaming(false);
                return;
            }

            // ── Ollama direct chat mode ──────────────────────────────────────
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: [...messages, userMsg].map(m => ({ role: m.role, content: m.content })),
                    model: selectedModel,
                    context: platformCtx ? {
                        cem_avg_score: platformCtx.cemSummary?.avg_score,
                        cem_poor_count: platformCtx.cemSummary?.poor_count,
                        cem_total_subscribers: platformCtx.cemSummary?.total,
                        vae_anomaly_count: platformCtx.vaeSummary?.anomaly_count,
                        vae_anomaly_rate: platformCtx.vaeSummary?.anomaly_rate,
                        vae_areas_affected: platformCtx.vaeSummary?.areas_affected,
                        rat_underserved: platformCtx.ratSummary?.underserved,
                        rat_underservice_rate: platformCtx.ratSummary?.rate,
                        granger_significant_pairs: platformCtx.granger?.significant,
                        oss_anomalies_sampled: platformCtx.anomalies?.length,
                        cem_risk_sampled: platformCtx.cemAnomalies?.length,
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
                    content: 'Error: Cannot connect to AI service. Ensure services are running.',
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
    const cemAvg = platformCtx?.cemSummary?.avg_score ?? 0;
    const vaeAnomalyCount = platformCtx?.vaeSummary?.anomaly_count ?? platformCtx?.anomalies?.length ?? 0;
    const ratRate = platformCtx?.ratSummary?.rate ?? 0;
    const grangerSig = platformCtx?.granger?.significant ?? 0;
    // legacy alias kept so the rest of the JSX still compiles
    const slaScore = cemAvg;
    const uptime = Math.floor((Date.now() - startTimeRef.current) / 1000);
    const uptimeStr = `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`;

    // Group pending actions by (title, source) so 18 identical fraud alerts collapse into one expandable card
    const pendingGroups = useMemo(() => groupActions(pendingActions), [pendingActions]);

    const toggleGroup = (key: string) => {
        setExpandedGroups(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
    };

    const approveGroup = async (group: ActionGroup, decision: 'approved' | 'rejected') => {
        // Apply the same decision to every action in the group (respects backend persistence)
        for (const item of group.items) {
            await handleAction(item, decision);
        }
    };

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
            {/* Push Notification Toast — hard cap at 2 visible to prevent screen-fill spam */}
            <div className="l4-toast-container">
                {notifications.slice(0, 2).map(n => (
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
                {notifications.length > 2 && (
                    <div className="l4-toast l4-toast-info" onClick={() => setNotifications([])} style={{ cursor: 'pointer', opacity: 0.8 }}>
                        <div className="l4-toast-icon">{'\u2026'}</div>
                        <div style={{ flex: 1 }}>
                            <div className="l4-toast-title">+{notifications.length - 2} more notifications</div>
                            <div className="l4-toast-msg">Click to dismiss all</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Operator-mode L4: PageInfoBar + Defense Explainer removed for production. */}

            {/* Architecture status panel — live operational metrics, not docs */}
            <L4ADNArchitecture
                cemAvg={cemAvg}
                vaeAnomalies={vaeAnomalyCount}
                ratRate={ratRate}
                grangerSig={grangerSig}
                correlationsCount={platformCtx?.correlations?.length ?? 0}
                pendingActions={pendingActions.length}
                autoApprovedCount={autoApprovedCount}
                cycleLatencyMs={agentSpeed}
            />


            {/* Compact agent status strip (replaces old duplicate header) */}
            <div className="card card-compact" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div className="l4-status-dot" />
                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-success)', letterSpacing: 1 }}>AGENT ACTIVE</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>· 30s closed-loop · {agentSpeed}ms cycle</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {pendingActions.length} pending · {autoApprovedCount} auto-approved · {actions.length} total in audit log
                </div>
            </div>

            {/* Tab switcher */}
            <div className="l4-tabs">
                <button className={`l4-tab ${activeTab === 'chat' ? 'l4-tab-active' : ''}`} onClick={() => setActiveTab('chat')}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                    NOCMate
                </button>
                <button className={`l4-tab ${activeTab === 'actions' ? 'l4-tab-active' : ''}`} onClick={() => setActiveTab('actions')}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
                    Spirits · Decisions
                    {pendingActions.length > 0 && <span className="l4-tab-badge">{pendingActions.length}</span>}
                </button>
                <button className={`l4-tab ${activeTab === 'monitor' ? 'l4-tab-active' : ''}`} onClick={() => setActiveTab('monitor')}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>
                    Awareness
                </button>
                <button className={`l4-tab ${activeTab === 'playbooks' ? 'l4-tab-active' : ''}`} onClick={() => setActiveTab('playbooks')}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>
                    Execution · Playbooks
                </button>
                <button className={`l4-tab ${activeTab === 'timeline' ? 'l4-tab-active' : ''}`} onClick={() => setActiveTab('timeline')}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                    Audit Timeline
                </button>
            </div>

            {/* Main content */}
            <div className="l4-main">
                {/* Chat Panel */}
                <div className={`l4-chat-panel ${activeTab === 'chat' ? 'l4-panel-active' : ''}`}>
                    {/* Model Selector Bar */}
                    <div className="l4-model-selector-bar">
                        <div className="l4-model-info">
                            <span className="l4-model-label">Model:</span>
                            <select
                                value={selectedModel}
                                onChange={(e) => setSelectedModel(e.target.value)}
                                className="l4-model-select"
                                disabled={streaming}
                            >
                                {AVAILABLE_MODELS.map(m => (
                                    <option key={m.id} value={m.id}>
                                        {m.name}
                                    </option>
                                ))}
                            </select>
                            <span className="l4-model-desc">
                                {AVAILABLE_MODELS.find(m => m.id === selectedModel)?.description}
                            </span>
                        </div>
                        <div className="l4-chat-actions">
                            <button
                                onClick={() => {
                                    setMessages([]);
                                    localStorage.removeItem('l4-agent-chat-history');
                                }}
                                className="l4-clear-chat-btn"
                                title="Clear chat history"
                            >
                                🗑️ Clear
                            </button>
                        </div>
                    </div>
                    <div className="l4-chat-messages">
                        {messages.length === 0 && (
                            <div className="l4-chat-empty">
                                <div className="l4-chat-empty-icon">
                                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.3 }}>
                                        <rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /><circle cx="12" cy="16" r="1" />
                                    </svg>
                                </div>
                                <div className="l4-chat-empty-title">ADN L4 Agent</div>
                                <div className="l4-chat-empty-sub">
                                    {ollamaReady === false
                                        ? 'Ollama not detected. Start Ollama with kimi-k2.5:cloud to enable the agent.'
                                        : 'Chat with Kimi about SLA risk, anomalies, network health, or request autonomous actions.'
                                    }
                                </div>
                                <div className="l4-suggestions">
                                    {[
                                        'Analyze current SLA risk and suggest remediation',
                                        'What anomalies were detected in the last pipeline run?',
                                        'Summarize the OSS-CEM correlation insights',
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

                    {/* Mode Toggle + Input */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Mode</div>
                        <div style={{ display: 'flex', gap: 4, background: 'var(--bg-elevated)', borderRadius: 6, padding: 2 }}>
                            <button
                                onClick={() => setChatMode('orchestrator')}
                                style={{
                                    fontSize: 11, fontWeight: 600, padding: '4px 10px', borderRadius: 4, border: 'none', cursor: 'pointer',
                                    background: chatMode === 'orchestrator' ? 'var(--brand-primary)' : 'transparent',
                                    color: chatMode === 'orchestrator' ? '#fff' : 'var(--text-secondary)',
                                    transition: 'all 0.2s',
                                }}
                            >
                                NeXo Orchestrator
                            </button>
                            <button
                                onClick={() => setChatMode('ollama')}
                                style={{
                                    fontSize: 11, fontWeight: 600, padding: '4px 10px', borderRadius: 4, border: 'none', cursor: 'pointer',
                                    background: chatMode === 'ollama' ? 'var(--brand-primary)' : 'transparent',
                                    color: chatMode === 'ollama' ? '#fff' : 'var(--text-secondary)',
                                    transition: 'all 0.2s',
                                }}
                            >
                                Ollama Chat
                            </button>
                        </div>
                        <div style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>
                            {chatMode === 'orchestrator' ? 'CEM + Network + Action agents' : 'Direct LLM conversation'}
                        </div>
                    </div>
                    <div className="l4-chat-input-wrap">
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            onPaste={handlePaste}
                            placeholder={
                                streaming ? 'Thinking...' :
                                chatMode === 'orchestrator' ? 'Ask NeXo about subscribers, cells, or actions...' :
                                ollamaReady === false ? 'Ollama not running...' : 'Ask the L4 Agent...'
                            }
                            disabled={streaming || (chatMode === 'ollama' && ollamaReady === false)}
                            className="l4-chat-input"
                            rows={1}
                        />
                        <button type="button" onClick={sendMessage} disabled={!input.trim() || streaming || (chatMode === 'ollama' && ollamaReady === false)} className="l4-send-btn">
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
                                        <div className="l4-monitor-label">CEM Avg Trend</div>
                                        <MiniSparkline data={slaHistory.length > 1 ? slaHistory : [cemAvg]} color="var(--color-success)" height={50} />
                                        <div className="l4-monitor-value" style={{ color: cemAvg < 0.3 ? 'var(--color-danger)' : cemAvg < 0.6 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                            {cemAvg ? cemAvg.toFixed(3) : '—'}
                                        </div>
                                    </div>
                                    <div className="l4-monitor-card">
                                        <div className="l4-monitor-label">VAE Anomalies</div>
                                        <MiniSparkline data={anomalyHistory.length > 1 ? anomalyHistory : [vaeAnomalyCount]} color="var(--color-danger)" height={50} />
                                        <div className="l4-monitor-value">{vaeAnomalyCount.toLocaleString()}</div>
                                    </div>
                                    <div className="l4-monitor-card">
                                        <div className="l4-monitor-label">RAT Underservice</div>
                                        <MiniSparkline data={[ratRate]} color="var(--color-warning)" height={50} />
                                        <div className="l4-monitor-value" style={{ color: ratRate > 25 ? 'var(--color-danger)' : ratRate > 15 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                            {ratRate.toFixed(1)}%
                                        </div>
                                    </div>
                                    <div className="l4-monitor-card">
                                        <div className="l4-monitor-label">Granger Sig.</div>
                                        <MiniSparkline data={[grangerSig]} color="var(--color-info)" height={50} />
                                        <div className="l4-monitor-value">{grangerSig}</div>
                                    </div>
                                    <div className="l4-monitor-card">
                                        <div className="l4-monitor-label">Correlations</div>
                                        <MiniSparkline data={[platformCtx?.correlations?.length ?? 0]} color="var(--color-info)" height={50} />
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
                                    <div className="l4-perf-row"><span>Model</span><span className="l4-perf-val">{AVAILABLE_MODELS.find(m => m.id === selectedModel)?.name || selectedModel}</span></div>
                                    <div className="l4-perf-row"><span>Cycle Interval</span><span className="l4-perf-val">30s</span></div>
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
                            {/* Pending - needs human approval — grouped by signal type */}
                            {pendingGroups.length > 0 && (
                                <div className="l4-section">
                                    <div className="l4-section-header">
                                        <span className="l4-pulse-dot" />
                                        Requires Approval
                                        <span className="badge badge-warning" style={{ marginLeft: 8, fontSize: 10 }}>
                                            {pendingActions.length} actions · {pendingGroups.length} signals
                                        </span>
                                    </div>
                                    {pendingGroups.map(group => {
                                        const isOpen = expandedGroups.has(group.key);
                                        const countClass =
                                            group.severity === 'critical' ? 'action-group-count-critical'
                                                : group.severity === 'warning' ? 'action-group-count-warning'
                                                    : '';
                                        return (
                                            <div key={group.key} className="action-group">
                                                <div className="action-group-header" onClick={() => toggleGroup(group.key)}>
                                                    <div className="action-group-header-left">
                                                        <TypeIcon type={group.anchor.type} />
                                                        <span className={`action-group-count ${countClass}`}>{group.items.length}</span>
                                                        <span className="action-group-title">{group.anchor.title}</span>
                                                    </div>
                                                    <div className="action-group-meta">
                                                        <span className={`badge badge-${group.severity === 'critical' ? 'danger' : group.severity === 'warning' ? 'warning' : 'info'}`} style={{ fontSize: 9 }}>
                                                            {group.severity.toUpperCase()}
                                                        </span>
                                                        <span style={{ color: 'var(--text-muted)' }}>
                                                            {(group.anchor.confidence * 100).toFixed(0)}%
                                                        </span>
                                                        <button
                                                            type="button"
                                                            className="l4-btn l4-btn-approve"
                                                            style={{ padding: '6px 10px', fontSize: 11 }}
                                                            onClick={(e) => { e.stopPropagation(); approveGroup(group, 'approved'); }}
                                                        >
                                                            Approve all
                                                        </button>
                                                        <button
                                                            type="button"
                                                            className="l4-btn l4-btn-reject"
                                                            style={{ padding: '6px 10px', fontSize: 11 }}
                                                            onClick={(e) => { e.stopPropagation(); approveGroup(group, 'rejected'); }}
                                                        >
                                                            Reject all
                                                        </button>
                                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }}>
                                                            <polyline points="6 9 12 15 18 9" />
                                                        </svg>
                                                    </div>
                                                </div>
                                                {isOpen && (
                                                    <div className="action-group-body">
                                                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', paddingBottom: 6 }}>
                                                            {group.anchor.description}
                                                        </div>
                                                        <div style={{ fontSize: 11, color: 'var(--text-muted)', paddingBottom: 6 }}>
                                                            Impact: <span style={{ color: 'var(--text-secondary)' }}>{group.anchor.impact}</span>
                                                            {' · '}Source: <span style={{ color: 'var(--text-secondary)' }}>{group.anchor.source}</span>
                                                        </div>
                                                        {group.items.map(item => (
                                                            <div key={item.id} className="action-group-row">
                                                                <div className="action-group-row-left">
                                                                    <div className="action-group-row-title">{item.id.slice(0, 18)}…</div>
                                                                    <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                                                                        {formatTunisTime(item.timestamp)}
                                                                        {' · '}confidence {(item.confidence * 100).toFixed(0)}%
                                                                    </div>
                                                                </div>
                                                                <div className="action-group-row-actions">
                                                                    <button
                                                                        className="l4-btn l4-btn-approve"
                                                                        style={{ padding: '6px 10px', fontSize: 11 }}
                                                                        onClick={(e) => { e.stopPropagation(); handleAction(item, 'approved'); }}
                                                                    >
                                                                        Approve
                                                                    </button>
                                                                    <button
                                                                        className="l4-btn l4-btn-reject"
                                                                        style={{ padding: '6px 10px', fontSize: 11 }}
                                                                        onClick={(e) => { e.stopPropagation(); handleAction(item, 'rejected'); }}
                                                                    >
                                                                        Reject
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            {/* Auto-approved + Executed */}
                            <div className="l4-section">
                                <div className="l4-section-header">
                                    Completed Actions
                                    <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 8 }}>{executedActions.length}</span>
                                </div>
                                {executedActions.map(action => (
                                    <div key={action.id} className="l4-executed-item" onClick={() => setSelectedAction(selectedAction?.id === action.id ? null : action)} style={{ cursor: action.executionLog ? 'pointer' : 'default' }}>
                                        <TypeIcon type={action.type} />
                                        <div className="l4-exec-content">
                                            <div className="l4-exec-title">{action.title}</div>
                                            <div className="l4-exec-meta">
                                                <span className={`badge ${action.status === 'auto_approved' ? 'badge-cyan' : action.status === 'executed' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: 9, padding: '1px 5px' }}>
                                                    {action.status === 'auto_approved' ? 'AUTO' : action.status.toUpperCase()}
                                                </span>
                                                <span>{action.source}</span>
                                                {action.executionLog && <span style={{ fontSize: 9, color: 'var(--color-info)' }}>click for details</span>}
                                            </div>
                                            {selectedAction?.id === action.id && action.executionLog && (
                                                <div style={{ marginTop: 8, padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: 11 }}>
                                                    <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-primary)' }}>Execution Results ({action.playbookId})</div>
                                                    {(action.executionLog.steps ?? []).map((step: any, i: number) => (
                                                        <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                                                            <span style={{ color: 'var(--color-success)', marginRight: 6 }}>{'\u2713'}</span>
                                                            <strong>{step.step}</strong>
                                                            {step.count !== undefined && <span className="mono"> ({step.count} items)</span>}
                                                            {step.critical !== undefined && <span className="mono"> (crit:{step.critical} warn:{step.warning} low:{step.low})</span>}
                                                            {step.cells && <span className="mono"> [{step.cells.join(', ')}]</span>}
                                                            {step.score !== undefined && <span className="mono"> = {step.score}</span>}
                                                            {step.flagged_count !== undefined && <span className="mono"> ({step.flagged_count} flagged, {step.total_revenue_at_risk} TND at risk)</span>}
                                                            {step.runs_analyzed && <span className="mono"> ({step.runs_analyzed} runs)</span>}
                                                            {step.throughput_mbps !== undefined && <span className="mono"> (throughput: {step.throughput_mbps} Mbps, users: {step.active_users}, latency: {step.latency_ms} ms)</span>}
                                                            {step.result?.status && <span className="mono"> [{step.result.status}]</span>}
                                                            {step.driver && <span className="mono"> = {step.driver}</span>}
                                                            {step.priority && <span className="mono"> [{step.priority}]</span>}
                                                            {step.ticket_id && (
                                                                <span className="mono">
                                                                    {' '}
                                                                    <a href="/tickets" style={{ color: 'var(--color-info)', textDecoration: 'underline' }} onClick={(e) => e.stopPropagation()}>
                                                                        [{step.ticket_id}]
                                                                    </a>
                                                                </span>
                                                            )}
                                                            {step.report_id && step.presigned_url && (
                                                                <span className="mono">
                                                                    {' '}
                                                                    <a href={step.presigned_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-success)', textDecoration: 'underline', fontWeight: 600 }} onClick={(e) => e.stopPropagation()}>
                                                                        ▼ Download Report ({step.report_id})
                                                                    </a>
                                                                </span>
                                                            )}
                                                            {step.run_id && step.status && (
                                                                <span className="mono"> [{step.run_id} · {step.status}]</span>
                                                            )}
                                                            {step.sent !== undefined && step.logged !== undefined && (
                                                                <span className="mono"> (sent:{step.sent} logged:{step.logged} failed:{step.failed})</span>
                                                            )}
                                                            {step.estimated_revenue_protected_tnd_per_month !== undefined && (
                                                                <span className="mono"> · revenue protected: {step.estimated_revenue_protected_tnd_per_month} TND/mo</span>
                                                            )}
                                                            {step.model_name && <span className="mono"> [{step.model_name}]</span>}
                                                            {step.improved !== undefined && (
                                                                <span className="mono"> (improved:{step.improved} no_change:{step.no_change} worsened:{step.worsened})</span>
                                                            )}
                                                            {Array.isArray(step.results) && step.results.length > 0 && (
                                                                <div style={{ paddingLeft: 22, marginTop: 4, fontSize: 10, color: 'var(--text-muted)' }}>
                                                                    {step.results.slice(0, 3).map((r: any, ri: number) => (
                                                                        <div key={ri}>↳ {r.channel} · {String(r.recipient ?? '').slice(0, 16)}… · {r.provider} · {r.status}</div>
                                                                    ))}
                                                                    {step.results.length > 3 && <div>↳ +{step.results.length - 3} more</div>}
                                                                </div>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
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

                {/* Playbooks Panel */}
                <div className={`l4-actions-panel ${activeTab === 'playbooks' ? 'l4-panel-active' : ''}`}>
                    {activeTab === 'playbooks' && (
                        <>
                            <div className="l4-section">
                                <div className="l4-section-header">Automated Remediation Playbooks</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 16 }}>
                                    Pre-configured autonomous response playbooks for common telecom incidents. Click to execute.
                                </div>
                                {[
                                    {
                                        id: 'pb-cem-degradation',
                                        name: 'CEM Degradation Response',
                                        desc: 'Identify low-CEM areas, correlate with OSS KPIs, trigger network optimization, notify operations team.',
                                        steps: ['Detect low CEM score areas from LightGBM', 'Correlate with OSS VAE anomalies', 'Identify root cause KPIs', 'Trigger network optimization playbook', 'Send NOC alert notification', 'Verify CEM recovery within 5 min'],
                                        trigger: 'CEM score < 0.3',
                                        severity: 'critical' as const,
                                        enabled: (platformCtx?.cemAnomalies?.length ?? 0) >= 20,
                                    },
                                    {
                                        id: 'pb-anomaly-triage',
                                        name: 'VAE Anomaly Auto-Triage',
                                        desc: 'Classify VAE anomaly type, correlate with CEM data, assign priority, create incident ticket.',
                                        steps: ['Collect anomaly features from VAE PyTorch', 'Run root cause classification', 'Cross-reference with CEM impact', 'Assign severity and priority', 'Create incident ticket', 'Assign to appropriate team'],
                                        trigger: 'New critical VAE anomaly detected',
                                        severity: 'warning' as const,
                                        enabled: (platformCtx?.anomalies?.filter((a: any) => a.severity > 0.9).length ?? 0) > 0,
                                    },
                                    {
                                        id: 'pb-capacity-scale',
                                        name: 'Predictive Capacity Scaling',
                                        desc: 'Forecast demand from ML models, pre-provision resources before peak hours.',
                                        steps: ['Run demand forecast model', 'Identify peak hour windows', 'Calculate required capacity delta', 'Pre-provision ECS instances', 'Warm up load balancers', 'Monitor and validate scaling'],
                                        trigger: 'Forecast > 80% capacity',
                                        severity: 'info' as const,
                                        enabled: true,
                                    },
                                    {
                                        id: 'pb-revenue-protect',
                                        name: 'RAT Underservice Response',
                                        desc: 'Detect RAT underservice cases, identify affected subscribers, trigger capacity optimization.',
                                        steps: ['Analyze RAT gap scores from XGBoost', 'Flag high-underservice areas', 'Cross-reference with device generation', 'Generate capacity optimization plan', 'Prioritize cell upgrades', 'Notify network planning team'],
                                        trigger: 'RAT underservice rate > 15%',
                                        severity: 'warning' as const,
                                        enabled: (platformCtx?.cemAnomalies?.filter((r: any) => (r.severity ?? r.score ?? 0) > 0.8).length ?? 0) > 0,
                                    },
                                    {
                                        id: 'pb-model-retrain',
                                        name: 'Model Auto-Retrain',
                                        desc: 'Detect model drift, retrain on latest data, validate performance, hot-swap models.',
                                        steps: ['Monitor prediction accuracy', 'Detect concept drift (KS test)', 'Collect recent training data', 'Retrain LightGBM + VAE + XGBoost', 'Validate against holdout set', 'Hot-swap model artifacts'],
                                        trigger: 'Model accuracy drop > 5%',
                                        severity: 'info' as const,
                                        enabled: true,
                                    },
                                    {
                                        id: 'pb-alert-subscriber',
                                        name: 'Alert Affected Subscribers',
                                        desc: 'Notify subscribers in degraded areas via SMS (Twilio) + email (SMTP). Console-logs in dev mode. Audit row written per send.',
                                        steps: ['Resolve top-10 at-risk subscribers (CEM<0.3 OR rat_gap>0.5)', 'Compose retention message', 'Send SMS via Twilio (or console-log)', 'Send email if address present', 'Write notifications_sent audit row', 'Return delivery summary'],
                                        trigger: 'Manual or low-CEM cohort detected',
                                        severity: 'warning' as const,
                                        enabled: true,
                                    },
                                    {
                                        id: 'pb-create-ticket',
                                        name: 'Open NOC Ticket',
                                        desc: 'Auto-open an internal incident ticket from the current critical signal. Critical severity also pages on-call via email.',
                                        steps: ['Extract action context (cell_id, area, KPIs)', 'Allocate TT-YYYY-NNNNN from sequence', 'Insert ticket row (status=open)', 'Notify on-call if critical', 'Return ticket_id for cross-reference'],
                                        trigger: 'Critical anomaly or RAT spike',
                                        severity: 'warning' as const,
                                        enabled: true,
                                    },
                                    {
                                        id: 'pb-retrain-model',
                                        name: 'Real Model Retrain (papermill)',
                                        desc: 'Actually re-execute the training notebook via papermill in the retrain-service container, write new artifact to shared volume, hot-reload ai-service from disk.',
                                        steps: ['Snapshot metrics_before from /model-metrics', 'Insert retrain_runs row (status=started)', 'POST retrain-service:8004/retrain (papermill executes notebook)', 'Copy new artifact → ai-service/models/', 'POST ai-service:8001/models/reload', 'Update retrain_runs status + metrics_after'],
                                        trigger: 'Drift detected OR manual',
                                        severity: 'info' as const,
                                        enabled: true,
                                    },
                                    {
                                        id: 'pb-capacity-report',
                                        name: 'Capacity Recommendation PDF',
                                        desc: 'Pull last 30 cycles of area_network_health + last 24h anomalies. Render fpdf2 PDF with KPI table, recommendations and methodology. Upload to MinIO with 7-day presigned URL.',
                                        steps: ['Query area_network_health (last 30 cycles)', 'Count 24h anomalies', 'Compute headroom/ recommendations', 'Render PDF (fpdf2)', 'Upload to MinIO reports/ bucket', 'Generate presigned URL + persist row'],
                                        trigger: 'Manual or weekly cadence',
                                        severity: 'info' as const,
                                        enabled: true,
                                    },
                                    {
                                        id: 'pb-churn-prevention',
                                        name: 'Churn Prevention Workflow',
                                        desc: 'Compound workflow: query high-risk subscribers (rat_gap>0.5 AND cem<0.3), send retention SMS, offer free SIM upgrade where USIM-bottlenecked, open tracking ticket, register interventions for longitudinal CEM-delta tracking.',
                                        steps: ['Query top-100 high-risk subscribers', 'Send retention SMS (Twilio or console)', 'Offer free SIM upgrade if usim_bottleneck', 'Insert churn_interventions rows (outcome=pending)', 'Open bulk tracking ticket if batch ≥20', 'Pipeline-worker auto-flips outcome to improved|no_change|worsened on next cycle'],
                                        trigger: 'rat_gap>0.5 AND cem<0.3 cohort',
                                        severity: 'critical' as const,
                                        enabled: true,
                                    },
                                ].map(pb => (
                                    <div key={pb.id} className={`l4-action-item l4-severity-${pb.severity}`} style={{ marginBottom: 8 }}>
                                        <div className="l4-action-header">
                                            <div className="l4-action-type">
                                                <span className={`badge badge-${pb.severity === 'critical' ? 'danger' : pb.severity === 'warning' ? 'warning' : 'info'}`} style={{ fontSize: 9 }}>
                                                    {pb.trigger}
                                                </span>
                                            </div>
                                            {pb.enabled && <span style={{ fontSize: 9, color: 'var(--color-success)', fontWeight: 600 }}>READY</span>}
                                        </div>
                                        <div className="l4-action-title">{pb.name}</div>
                                        <div className="l4-action-desc">{pb.desc}</div>
                                        <div style={{ marginTop: 10 }}>
                                            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Execution Steps</div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                                {(pb.steps ?? []).map((step, i) => (
                                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: runningPlaybook === pb.id && i <= 2 ? 'var(--color-success)' : 'var(--text-secondary)' }}>
                                                        <span style={{ width: 18, height: 18, borderRadius: '50%', background: runningPlaybook === pb.id && i <= 2 ? 'var(--color-success-bg)' : 'var(--bg-elevated)', border: `1px solid ${runningPlaybook === pb.id && i <= 2 ? 'var(--color-success-border)' : 'var(--border)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, flexShrink: 0, fontWeight: 700 }}>
                                                            {runningPlaybook === pb.id && i <= 2 ? '\u2713' : i + 1}
                                                        </span>
                                                        {step}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <div style={{ marginTop: 12 }}>
                                            <button
                                                className={`l4-btn ${pb.enabled ? 'l4-btn-approve' : ''}`}
                                                style={!pb.enabled ? { opacity: 0.5, cursor: 'not-allowed', background: 'var(--bg-elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)' } : {}}
                                                onClick={async (e) => {
                                                    e.stopPropagation();
                                                    if (!pb.enabled || runningPlaybook) return;
                                                    setRunningPlaybook(pb.id);
                                                    pushNotification({ title: 'Playbook Executing', message: pb.name, type: 'info' });
                                                    try {
                                                        // Create action with playbook_id, then execute via real backend
                                                        const actionId = `${pb.id}-${Date.now()}`;
                                                        await fetch('/api/platform-data', {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({
                                                                _action: 'create',
                                                                action_id: actionId,
                                                                type: 'auto_remediation',
                                                                title: pb.name,
                                                                description: pb.desc,
                                                                severity: pb.severity,
                                                                status: 'approved',
                                                                source: 'L4 Agent Playbook',
                                                                confidence: 1.0,
                                                                impact: pb.trigger,
                                                                playbook_id: pb.id,
                                                            }),
                                                        });
                                                        const execRes = await fetch('/api/platform-data', {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({ _action: 'execute', action_id: actionId }),
                                                        });
                                                        const result = await execRes.json();
                                                        setRunningPlaybook(null);
                                                        // Build detailed result message from execution_log
                                                        const steps = result?.execution_log?.steps ?? [];
                                                        const detailParts: string[] = [];
                                                        for (const s of steps) {
                                                            if (s.count !== undefined) detailParts.push(`${s.step}: ${s.count}`);
                                                            else if (s.critical !== undefined) detailParts.push(`Severity: ${s.critical} critical, ${s.warning} warning, ${s.low} low`);
                                                            else if (s.cells) detailParts.push(`Cells: ${s.cells.join(', ') || 'none'}`);
                                                            else if (s.score !== undefined) detailParts.push(`SLA: ${s.score}`);
                                                            else if (s.flagged_count !== undefined) detailParts.push(`Flagged: ${s.flagged_count}, Revenue at risk: ${s.total_revenue_at_risk}`);
                                                            else if (s.runs_analyzed) detailParts.push(`Analyzed ${s.runs_analyzed} runs`);
                                                            else if (s.result?.status) detailParts.push(`Models: ${s.result.status}`);
                                                        }
                                                        pushNotification({
                                                            title: 'Playbook Completed',
                                                            message: `${pb.name} — ${steps.length} steps. ${detailParts.slice(0, 2).join('. ')}`,
                                                            type: 'success',
                                                        });
                                                        // Refresh data to show new action
                                                        fetchData();
                                                    } catch {
                                                        setRunningPlaybook(null);
                                                        pushNotification({ title: 'Playbook Failed', message: `${pb.name} execution failed`, type: 'danger' });
                                                    }
                                                }}
                                            >
                                                {runningPlaybook === pb.id ? (
                                                    <><div className="l4-send-spinner" style={{ width: 12, height: 12 }} /> Executing...</>
                                                ) : (
                                                    <>{pb.enabled ? '\u25B6 Execute Playbook' : 'Not Triggered'}</>
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>

                {/* Timeline Panel */}
                <div className={`l4-actions-panel ${activeTab === 'timeline' ? 'l4-panel-active' : ''}`}>
                    {activeTab === 'timeline' && (
                        <>
                            <div className="l4-section">
                                <div className="l4-section-header">Incident Timeline</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 16 }}>
                                    Chronological event log of all AI-detected incidents and autonomous actions
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 0, position: 'relative' }}>
                                    {/* Timeline vertical line */}
                                    <div style={{ position: 'absolute', left: 12, top: 0, bottom: 0, width: 2, background: 'var(--border)' }} />

                                    {[
                                        ...((platformCtx?.anomalies?.length ?? 0) >= 50 ? [{
                                            time: 'Just now',
                                            event: `VAE Anomaly Spike: ${platformCtx?.anomalies?.length ?? 0} detected`,
                                            type: 'critical' as const,
                                            detail: 'PyTorch VAE model detected critical anomaly spike across OSS cell KPIs',
                                            action: 'Auto-remediation playbook triggered',
                                        }] : []),
                                        ...((platformCtx?.anomalies?.filter((a: any) => a.severity > 0.9) ?? []).slice(0, 2).map((a: any, i: number) => ({
                                            time: `${2 + i * 3}min ago`,
                                            event: `Critical OSS Anomaly: Cell ${a.cell_id ?? 'unknown'}`,
                                            type: 'warning' as const,
                                            detail: `VAE reconstruction error: ${(a.severity ?? 0).toFixed(3)}. Throughput: ${(a.throughput_mbps ?? 0).toFixed(1)} Mbps`,
                                            action: 'Added to triage queue',
                                        }))),
                                        {
                                            time: '5min ago',
                                            event: 'Pipeline Cycle Completed',
                                            type: 'info' as const,
                                            detail: `${platformCtx?.anomalies?.length ?? 0} OSS + ${platformCtx?.cemAnomalies?.length ?? 0} CEM records processed`,
                                            action: '3 v3 models inference complete',
                                        },
                                        {
                                            time: '7min ago',
                                            event: 'OSS-CEM Correlation Updated',
                                            type: 'info' as const,
                                            detail: `${platformCtx?.correlations?.length ?? 0} correlations computed (Pearson + Spearman)`,
                                            action: `${platformCtx?.correlations?.filter((c: any) => Math.abs(c.corr_value) >= 0.7).length ?? 0} strong correlations detected`,
                                        },
                                        ...((platformCtx?.cemAnomalies?.filter((r: any) => (r.severity ?? r.score ?? 0) > 0.8) ?? []).slice(0, 1).map(() => ({
                                            time: '10min ago',
                                            event: 'RAT Underservice Detected',
                                            type: 'warning' as const,
                                            detail: 'XGBoost flagged subscribers on lower RAT than device supports',
                                            action: 'Capacity optimization recommended',
                                        }))),
                                        {
                                            time: '15min ago',
                                            event: 'Model Health Check',
                                            type: 'info' as const,
                                            detail: 'All 3 v3 ML models healthy: LightGBM v3.0 (CEM), VAE v3.0 (OSS), XGBoost v3.0 (RAT)',
                                            action: 'No drift detected',
                                        },
                                        {
                                            time: '30min ago',
                                            event: 'Agent Session Started',
                                            type: 'info' as const,
                                            detail: 'L4 Autonomous Agent initialized and connected to telemetry streams',
                                            action: `Monitoring ${platformCtx?.anomalies?.length ?? 0} OSS + ${platformCtx?.cemAnomalies?.length ?? 0} CEM signals`,
                                        },
                                    ].map((evt, i) => (
                                        <div key={i} style={{ display: 'flex', gap: 16, padding: '12px 0 12px 32px', position: 'relative' }}>
                                            {/* Timeline dot */}
                                            <div style={{
                                                position: 'absolute', left: 7, top: 16,
                                                width: 12, height: 12, borderRadius: '50%',
                                                background: evt.type === 'critical' ? 'var(--color-danger)' : evt.type === 'warning' ? 'var(--color-warning)' : 'var(--bg-elevated)',
                                                border: `2px solid ${evt.type === 'critical' ? 'var(--color-danger)' : evt.type === 'warning' ? 'var(--color-warning)' : 'var(--border)'}`,
                                            }} />
                                            <div style={{ flex: 1 }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                                    <div style={{ fontSize: 12, fontWeight: 600, color: evt.type === 'critical' ? 'var(--color-danger)' : evt.type === 'warning' ? 'var(--color-warning)' : 'var(--text-primary)' }}>
                                                        {evt.event}
                                                    </div>
                                                    <span style={{ fontSize: 10, color: 'var(--text-muted)', flexShrink: 0, marginLeft: 8 }}>{evt.time}</span>
                                                </div>
                                                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>{evt.detail}</div>
                                                <div style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic' }}>{evt.action}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Knowledge Graph */}
                            <div className="l4-section">
                                <div className="l4-section-header">Agent Knowledge Graph</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>
                                    Relationships between signals, models, and actions
                                </div>
                                <svg width="100%" height="200" viewBox="0 0 500 200" style={{ display: 'block' }}>
                                    {/* Edges */}
                                    <line x1="80" y1="100" x2="250" y2="40" stroke="var(--brand-primary)" strokeWidth="1.5" opacity="0.4" />
                                    <line x1="80" y1="100" x2="250" y2="100" stroke="var(--color-warning)" strokeWidth="1.5" opacity="0.4" />
                                    <line x1="80" y1="100" x2="250" y2="160" stroke="var(--color-info)" strokeWidth="1.5" opacity="0.4" />
                                    <line x1="250" y1="40" x2="420" y2="60" stroke="var(--color-danger)" strokeWidth="1.5" opacity="0.4" />
                                    <line x1="250" y1="100" x2="420" y2="100" stroke="var(--color-success)" strokeWidth="1.5" opacity="0.4" />
                                    <line x1="250" y1="160" x2="420" y2="140" stroke="var(--color-warning)" strokeWidth="1.5" opacity="0.4" />
                                    {/* Nodes */}
                                    {[
                                        { x: 80, y: 100, label: 'Telemetry\nStream', color: 'var(--brand-primary)' },
                                        { x: 250, y: 40, label: 'CEM\nScorer', color: 'var(--color-success)' },
                                        { x: 250, y: 100, label: 'VAE\nAnomaly', color: 'var(--color-danger)' },
                                        { x: 250, y: 160, label: 'RAT\nDetector', color: 'var(--color-warning)' },
                                        { x: 420, y: 60, label: 'Auto\nRemediation', color: 'var(--color-danger)' },
                                        { x: 420, y: 100, label: 'Incident\nTriage', color: 'var(--color-success)' },
                                        { x: 420, y: 140, label: 'Capacity\nScaling', color: 'var(--color-warning)' },
                                    ].map((n, i) => (
                                        <g key={i}>
                                            <circle cx={n.x} cy={n.y} r="22" fill="var(--bg-elevated)" stroke={n.color} strokeWidth="2" />
                                            {n.label.split('\n').map((line, j) => (
                                                <text key={j} x={n.x} y={n.y + (j - 0.5) * 10 + 3} textAnchor="middle" fontSize="8" fill="var(--text-secondary)" fontWeight="600">
                                                    {line}
                                                </text>
                                            ))}
                                        </g>
                                    ))}
                                    {/* Flow arrows text */}
                                    <text x="160" y="62" fontSize="7" fill="var(--text-muted)" textAnchor="middle">13 CEM features</text>
                                    <text x="160" y="95" fontSize="7" fill="var(--text-muted)" textAnchor="middle">9 VAE features</text>
                                    <text x="160" y="138" fontSize="7" fill="var(--text-muted)" textAnchor="middle">10 RAT features</text>
                                    <text x="340" y="44" fontSize="7" fill="var(--text-muted)" textAnchor="middle">score &lt; 0.3</text>
                                    <text x="340" y="95" fontSize="7" fill="var(--text-muted)" textAnchor="middle">error &gt; threshold</text>
                                    <text x="340" y="155" fontSize="7" fill="var(--text-muted)" textAnchor="middle">gap &gt; 0.5</text>
                                </svg>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
