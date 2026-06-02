"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "./ThemeProvider";

interface CommandItem {
    id: string;
    label: string;
    description?: string;
    group: string;
    icon: React.ReactNode;
    action: () => void;
    keywords?: string[];
}

const CmdIcons = {
    page: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
            <polyline points="13 2 13 9 20 9" />
        </svg>
    ),
    playbook: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
        </svg>
    ),
    theme: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
    ),
    external: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
        </svg>
    ),
    action: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
    ),
    search: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
    ),
    logout: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
        </svg>
    ),
};

function fuzzyScore(query: string, text: string): number {
    const q = query.toLowerCase();
    const t = text.toLowerCase();
    if (t === q) return 100;
    if (t.startsWith(q)) return 80;
    if (t.includes(q)) return 60;
    let qi = 0;
    let score = 0;
    let lastMatch = -1;
    for (let ti = 0; ti < t.length && qi < q.length; ti++) {
        if (t[ti] === q[qi]) {
            score += 10;
            if (lastMatch === ti - 1) score += 5;
            lastMatch = ti;
            qi++;
        }
    }
    return qi === q.length ? score : 0;
}

// Fire a playbook through the existing SSR auth proxy.
// Pattern: create an action (idempotent), then execute it.
async function firePlaybook(playbookId: string, title: string, severity: string, metadata: Record<string, unknown> = {}) {
    try {
        const actionId = `cmdk-${playbookId}-${Date.now()}`;
        const createRes = await fetch("/api/platform-data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                _action: "create",
                action_id: actionId,
                title,
                severity,
                type: "remediation",
                confidence: 0.95,
                playbook_id: playbookId,
                description: `Triggered from command palette: ${title}`,
                metadata,
            }),
        });
        if (!createRes.ok) throw new Error(`create failed: ${createRes.status}`);

        const execRes = await fetch("/api/platform-data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ _action: "execute", action_id: actionId }),
        });
        if (!execRes.ok) throw new Error(`execute failed: ${execRes.status}`);
        return { ok: true, actionId };
    } catch (e: any) {
        console.error("[CmdK] playbook fire failed:", e?.message ?? e);
        return { ok: false, error: String(e?.message ?? e) };
    }
}

export default function CommandPalette() {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [activeIndex, setActiveIndex] = useState(0);
    const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const listRef = useRef<HTMLDivElement>(null);
    const router = useRouter();
    const { theme, toggleTheme } = useTheme();

    const close = useCallback(() => {
        setOpen(false);
        setQuery("");
        setActiveIndex(0);
    }, []);

    const flashToast = (msg: string, ok = true) => {
        setToast({ msg, ok });
        setTimeout(() => setToast(null), 3500);
    };

    const runPlaybook = useCallback(async (id: string, title: string, severity: string, meta: Record<string, unknown> = {}) => {
        close();
        flashToast(`Firing ${id}…`, true);
        const result = await firePlaybook(id, title, severity, meta);
        if (result.ok) {
            flashToast(`✓ ${id} executed`, true);
        } else {
            flashToast(`✗ ${id} failed`, false);
        }
    }, [close]);

    const commands: CommandItem[] = useMemo(() => [
        // ── Primary pages (story-arc order) ──
        { id: "nav-overview", label: "Overview", description: "Dashboard home with KPIs", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/overview"); close(); }, keywords: ["home", "dashboard", "kpi"] },
        { id: "nav-l4", label: "L4 Agent", description: "Autonomous operations workspace", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/l4-agent"); close(); }, keywords: ["agent", "autonomous", "remediation", "ai", "actuation"] },
        { id: "nav-granger", label: "Granger Causality", description: "OSS→CEM temporal causality proof", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/granger-causality"); close(); }, keywords: ["granger", "causality", "temporal", "lag", "lead-time"] },
        { id: "nav-correlations", label: "Correlations", description: "Pearson + Spearman OSS↔CEM matrix", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/correlations"); close(); }, keywords: ["pearson", "spearman", "convergence", "metrics"] },
        { id: "nav-cem", label: "CEM Scores", description: "Subscriber experience model (LightGBM)", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/cem-scores"); close(); }, keywords: ["cem", "subscriber", "lightgbm", "experience"] },
        { id: "nav-vae", label: "VAE Anomalies", description: "OSS experience anomaly model (PyTorch VAE)", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/vae-anomalies"); close(); }, keywords: ["vae", "anomaly", "oss", "pytorch", "autoencoder"] },
        { id: "nav-rat", label: "RAT Gap", description: "RAT underservice model (XGBoost)", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/rat-underservice"); close(); }, keywords: ["rat", "underservice", "xgboost", "radio", "2g", "3g", "4g"] },
        // ── Actuation pages ──
        { id: "nav-tickets", label: "Tickets", description: "NOC tickets (TT-YYYY-NNNNN)", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/tickets"); close(); }, keywords: ["ticket", "noc", "incident"] },
        { id: "nav-notifications", label: "Notifications", description: "SMS/email audit trail", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/notifications"); close(); }, keywords: ["sms", "email", "alert", "twilio"] },
        { id: "nav-interventions", label: "Interventions", description: "Churn intervention longitudinal tracking", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/interventions"); close(); }, keywords: ["churn", "intervention", "cem-delta", "outcome"] },
        { id: "nav-reports", label: "Reports", description: "Capacity recommendation PDFs", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/reports"); close(); }, keywords: ["pdf", "capacity", "report"] },
        // ── More pages ──
        { id: "nav-forecast", label: "Forecast", description: "Predictive analytics", group: "More Pages", icon: CmdIcons.page, action: () => { router.push("/predictive"); close(); }, keywords: ["forecast", "predict", "trend"] },
        { id: "nav-capacity", label: "Capacity", description: "Capacity planning & headroom", group: "More Pages", icon: CmdIcons.page, action: () => { router.push("/capacity"); close(); }, keywords: ["capacity", "headroom", "planning"] },
        { id: "nav-intelligence", label: "AI Intelligence", description: "RCA + anomaly timeline", group: "More Pages", icon: CmdIcons.page, action: () => { router.push("/intelligence"); close(); }, keywords: ["intelligence", "rca", "root cause", "timeline"] },
        { id: "nav-models", label: "Model Evaluation", description: "Real ML metrics (R², ROC-AUC)", group: "More Pages", icon: CmdIcons.page, action: () => { router.push("/model-evaluation"); close(); }, keywords: ["model", "evaluation", "metrics", "roc", "auc"] },
        { id: "nav-pipelines", label: "Pipeline Runs", description: "Pipeline execution history", group: "More Pages", icon: CmdIcons.page, action: () => { router.push("/pipeline-runs"); close(); }, keywords: ["pipeline", "runs", "execution"] },
        { id: "nav-health", label: "Health", description: "Platform observability", group: "More Pages", icon: CmdIcons.page, action: () => { router.push("/ops-metrics"); close(); }, keywords: ["health", "ops", "netdata", "prometheus"] },
        { id: "nav-dwh", label: "Data Warehouse", description: "DWH explorer", group: "More Pages", icon: CmdIcons.page, action: () => { router.push("/data-warehouse"); close(); }, keywords: ["dwh", "warehouse", "data", "tables"] },

        // ── Playbooks (fire from anywhere) ──
        { id: "pb-alert", label: "Alert subscribers", description: "Fire pb-alert-subscriber · SMS retention message", group: "Run Playbook", icon: CmdIcons.playbook, action: () => runPlaybook("pb-alert-subscriber", "Alert at-risk subscribers", "warning"), keywords: ["sms", "alert", "subscriber", "twilio", "notify"] },
        { id: "pb-ticket", label: "Create NOC ticket", description: "Fire pb-create-ticket · Opens TT-YYYY-NNNNN", group: "Run Playbook", icon: CmdIcons.playbook, action: () => runPlaybook("pb-create-ticket", "Create NOC ticket", "warning"), keywords: ["ticket", "noc", "open", "incident"] },
        { id: "pb-retrain-cem", label: "Retrain CEM model", description: "Fire pb-retrain-model · LightGBM via papermill", group: "Run Playbook", icon: CmdIcons.playbook, action: () => runPlaybook("pb-retrain-model", "Retrain CEM (LightGBM)", "info", { model_name: "cem" }), keywords: ["retrain", "cem", "lightgbm", "model"] },
        { id: "pb-retrain-rat", label: "Retrain RAT model", description: "Fire pb-retrain-model · XGBoost via papermill", group: "Run Playbook", icon: CmdIcons.playbook, action: () => runPlaybook("pb-retrain-model", "Retrain RAT (XGBoost)", "info", { model_name: "rat" }), keywords: ["retrain", "rat", "xgboost", "model"] },
        { id: "pb-retrain-vae", label: "Retrain VAE model", description: "Fire pb-retrain-model · PyTorch VAE via papermill", group: "Run Playbook", icon: CmdIcons.playbook, action: () => runPlaybook("pb-retrain-model", "Retrain VAE (PyTorch)", "info", { model_name: "vae" }), keywords: ["retrain", "vae", "pytorch", "anomaly", "model"] },
        { id: "pb-capacity-report", label: "Generate capacity report", description: "Fire pb-capacity-report · PDF to MinIO", group: "Run Playbook", icon: CmdIcons.playbook, action: () => runPlaybook("pb-capacity-report", "Generate capacity report", "info", { area: "ALL" }), keywords: ["pdf", "capacity", "report", "generate"] },
        { id: "pb-churn-prevention", label: "Run churn prevention", description: "Fire pb-churn-prevention · bulk SMS + tickets + tracking", group: "Run Playbook", icon: CmdIcons.playbook, action: () => runPlaybook("pb-churn-prevention", "Churn prevention sweep", "critical"), keywords: ["churn", "prevention", "retention", "sweep", "bulk"] },

        // ── Actions ──
        { id: "act-theme", label: `Switch to ${theme === "dark" ? "Light" : "Dark"} Theme`, description: "Toggle NeXo theme", group: "Actions", icon: CmdIcons.theme, action: () => { toggleTheme(); close(); }, keywords: ["theme", "dark", "light", "mode", "toggle"] },
        { id: "act-refresh", label: "Refresh Data", description: "Reload the current page data", group: "Actions", icon: CmdIcons.action, action: () => { router.refresh(); close(); }, keywords: ["reload", "refresh", "update"] },
        { id: "act-logout", label: "Sign Out", description: "Log out of the dashboard", group: "Actions", icon: CmdIcons.logout, action: () => { fetch("/api/logout", { method: "POST" }).then(() => { router.push("/login"); router.refresh(); }); close(); }, keywords: ["logout", "sign out", "exit"] },

        // ── External tools ──
        { id: "ext-minio", label: "Open MinIO Console", description: "Object storage management", group: "External Tools", icon: CmdIcons.external, action: () => { window.open("http://localhost:9001", "_blank"); close(); }, keywords: ["minio", "storage", "s3", "bucket"] },
        { id: "ext-netdata", label: "Open Netdata", description: "Real-time system & container monitoring", group: "External Tools", icon: CmdIcons.external, action: () => { window.open("http://localhost:19999", "_blank"); close(); }, keywords: ["netdata", "monitoring", "metrics", "system"] },
        { id: "ext-prometheus", label: "Open Prometheus", description: "Metrics explorer & TSDB", group: "External Tools", icon: CmdIcons.external, action: () => { window.open("http://localhost:9090", "_blank"); close(); }, keywords: ["prometheus", "metrics", "tsdb"] },
        { id: "ext-grafana", label: "Open Grafana", description: "Dashboards & visualization", group: "External Tools", icon: CmdIcons.external, action: () => { window.open("http://localhost:3000", "_blank"); close(); }, keywords: ["grafana", "dashboard"] },
        { id: "ext-jaeger", label: "Open Jaeger", description: "Distributed trace explorer", group: "External Tools", icon: CmdIcons.external, action: () => { window.open("http://localhost:16686", "_blank"); close(); }, keywords: ["jaeger", "tracing", "trace"] },
    ], [theme, toggleTheme, router, close, runPlaybook]);

    const filtered = useMemo(() => {
        if (!query.trim()) return commands;
        return commands
            .map((cmd) => {
                const searchText = `${cmd.label} ${cmd.description || ""} ${(cmd.keywords || []).join(" ")}`;
                const score = fuzzyScore(query, searchText);
                return { cmd, score };
            })
            .filter(({ score }) => score > 0)
            .sort((a, b) => b.score - a.score)
            .map(({ cmd }) => cmd);
    }, [query, commands]);

    const grouped = useMemo(() => {
        const groups: { label: string; items: CommandItem[] }[] = [];
        const seen = new Set<string>();
        for (const item of filtered) {
            if (!seen.has(item.group)) {
                seen.add(item.group);
                groups.push({ label: item.group, items: [] });
            }
            groups.find((g) => g.label === item.group)!.items.push(item);
        }
        return groups;
    }, [filtered]);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "k") {
                e.preventDefault();
                setOpen((prev) => !prev);
                if (!open) {
                    setQuery("");
                    setActiveIndex(0);
                }
            }
            if (e.key === "Escape" && open) {
                e.preventDefault();
                close();
            }
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [open, close]);

    useEffect(() => {
        if (open) requestAnimationFrame(() => inputRef.current?.focus());
    }, [open]);

    useEffect(() => {
        const el = listRef.current?.querySelector(`[data-index="${activeIndex}"]`);
        el?.scrollIntoView({ block: "nearest" });
    }, [activeIndex]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "ArrowDown") {
            e.preventDefault();
            setActiveIndex((i) => (i + 1) % Math.max(filtered.length, 1));
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActiveIndex((i) => (i - 1 + filtered.length) % Math.max(filtered.length, 1));
        } else if (e.key === "Enter") {
            e.preventDefault();
            filtered[activeIndex]?.action();
        }
    };

    useEffect(() => { setActiveIndex(0); }, [query]);

    let flatIndex = -1;

    return (
        <>
            {open && (
                <div className="cmd-overlay" onClick={close}>
                    <div className="cmd-palette" onClick={(e) => e.stopPropagation()} onKeyDown={handleKeyDown}>
                        <div className="cmd-input-wrap">
                            <span className="cmd-search-icon">{CmdIcons.search}</span>
                            <input
                                ref={inputRef}
                                className="cmd-input"
                                placeholder="Search pages, fire playbooks (try 'retrain rat', 'alert', 'churn')…"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                spellCheck={false}
                                autoComplete="off"
                            />
                            <kbd className="cmd-kbd">ESC</kbd>
                        </div>

                        <div className="cmd-results" ref={listRef}>
                            {filtered.length === 0 && (
                                <div className="cmd-empty">No results for &ldquo;{query}&rdquo;</div>
                            )}
                            {grouped.map((group) => (
                                <div key={group.label} className="cmd-group">
                                    <div className="cmd-group-label">{group.label}</div>
                                    {group.items.map((item) => {
                                        flatIndex++;
                                        const idx = flatIndex;
                                        return (
                                            <button
                                                type="button"
                                                key={item.id}
                                                data-index={idx}
                                                className={`cmd-item ${idx === activeIndex ? "cmd-item-active" : ""}`}
                                                onClick={item.action}
                                                onMouseEnter={() => setActiveIndex(idx)}
                                            >
                                                <span className="cmd-item-icon">{item.icon}</span>
                                                <span className="cmd-item-text">
                                                    <span className="cmd-item-label">{item.label}</span>
                                                    {item.description && <span className="cmd-item-desc">{item.description}</span>}
                                                </span>
                                                <span className="cmd-item-hint">
                                                    {idx === activeIndex && <span className="cmd-enter-hint">Enter ↵</span>}
                                                </span>
                                            </button>
                                        );
                                    })}
                                </div>
                            ))}
                        </div>

                        <div className="cmd-footer">
                            <span className="cmd-footer-hint"><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
                            <span className="cmd-footer-hint"><kbd>Enter</kbd> select</span>
                            <span className="cmd-footer-hint"><kbd>Esc</kbd> close</span>
                        </div>
                    </div>
                </div>
            )}
            {toast && (
                <div className={`cmd-toast ${toast.ok ? "cmd-toast-ok" : "cmd-toast-err"}`}>
                    {toast.msg}
                </div>
            )}
        </>
    );
}
