"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "./ThemeProvider";

/* ── Types ────────────────────────────────────────────────────────────────── */
interface CommandItem {
    id: string;
    label: string;
    description?: string;
    group: string;
    icon: React.ReactNode;
    action: () => void;
    keywords?: string[];
}

/* ── SVG Icons ────────────────────────────────────────────────────────────── */
const CmdIcons = {
    page: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
            <polyline points="13 2 13 9 20 9" />
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

/* ── Fuzzy match ──────────────────────────────────────────────────────────── */
function fuzzyMatch(query: string, text: string): boolean {
    const q = query.toLowerCase();
    const t = text.toLowerCase();
    if (t.includes(q)) return true;
    let qi = 0;
    for (let ti = 0; ti < t.length && qi < q.length; ti++) {
        if (t[ti] === q[qi]) qi++;
    }
    return qi === q.length;
}

function fuzzyScore(query: string, text: string): number {
    const q = query.toLowerCase();
    const t = text.toLowerCase();
    if (t === q) return 100;
    if (t.startsWith(q)) return 80;
    if (t.includes(q)) return 60;
    // subsequence score
    let qi = 0;
    let score = 0;
    let lastMatch = -1;
    for (let ti = 0; ti < t.length && qi < q.length; ti++) {
        if (t[ti] === q[qi]) {
            score += 10;
            if (lastMatch === ti - 1) score += 5; // consecutive bonus
            lastMatch = ti;
            qi++;
        }
    }
    return qi === q.length ? score : 0;
}

/* ── Component ────────────────────────────────────────────────────────────── */
export default function CommandPalette() {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [activeIndex, setActiveIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);
    const listRef = useRef<HTMLDivElement>(null);
    const router = useRouter();
    const { theme, toggleTheme } = useTheme();

    const close = useCallback(() => {
        setOpen(false);
        setQuery("");
        setActiveIndex(0);
    }, []);

    /* ── Commands registry ────────────────────────────────────────────────── */
    const commands: CommandItem[] = useMemo(() => [
        // Pages
        { id: "nav-overview", label: "Overview", description: "Dashboard home with KPIs", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/overview"); close(); }, keywords: ["home", "dashboard", "kpi"] },
        { id: "nav-sla", label: "SLA Risk", description: "Risk analysis & predictions", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/sla-risk"); close(); }, keywords: ["risk", "prediction", "breach", "score"] },
        { id: "nav-anomalies", label: "Anomalies", description: "OSS & BSS anomaly detection", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/anomalies"); close(); }, keywords: ["detection", "oss", "bss", "network", "revenue"] },
        { id: "nav-correlations", label: "Correlations", description: "O+B convergence analysis", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/correlations"); close(); }, keywords: ["pearson", "spearman", "convergence", "metrics"] },
        { id: "nav-intelligence", label: "AI Intelligence", description: "Root cause analysis & anomaly timeline", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/intelligence"); close(); }, keywords: ["intelligence", "rca", "root cause", "timeline", "ai", "analysis", "narrative"] },
        { id: "nav-dwh", label: "Data Warehouse", description: "Browse raw, processed & operational data", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/data-warehouse"); close(); }, keywords: ["dwh", "warehouse", "data", "tables", "catalog", "raw", "records"] },
        { id: "nav-pipelines", label: "Pipeline Runs", description: "Data pipeline execution history", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/pipeline-runs"); close(); }, keywords: ["pipeline", "execution", "jobs", "runs"] },
        { id: "nav-health", label: "Ops Metrics", description: "Platform observability & health", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/ops-metrics"); close(); }, keywords: ["health", "grafana", "prometheus", "monitoring"] },
        { id: "nav-agent", label: "L4 Agent", description: "Autonomous operations workspace", group: "Pages", icon: CmdIcons.page, action: () => { router.push("/l4-agent"); close(); }, keywords: ["agent", "autonomous", "remediation", "ai"] },
        // Actions
        { id: "act-theme", label: `Switch to ${theme === "dark" ? "Light" : "Dark"} Theme`, description: "Toggle NexOps theme", group: "Actions", icon: CmdIcons.theme, action: () => { toggleTheme(); close(); }, keywords: ["theme", "dark", "light", "mode", "toggle"] },
        { id: "act-refresh", label: "Refresh Data", description: "Reload the current page data", group: "Actions", icon: CmdIcons.action, action: () => { router.refresh(); close(); }, keywords: ["reload", "refresh", "update"] },
        { id: "act-logout", label: "Sign Out", description: "Log out of the dashboard", group: "Actions", icon: CmdIcons.logout, action: () => { fetch("/api/logout", { method: "POST" }).then(() => { router.push("/login"); router.refresh(); }); close(); }, keywords: ["logout", "sign out", "exit"] },
        // External Tools
        { id: "ext-minio", label: "Open MinIO Console", description: "Object storage management", group: "External Tools", icon: CmdIcons.external, action: () => { window.open("http://localhost:9001", "_blank"); close(); }, keywords: ["minio", "storage", "s3", "bucket"] },
        { id: "ext-signoz", label: "Open SigNoz", description: "Observability — traces, metrics, logs", group: "External Tools", icon: CmdIcons.external, action: () => { window.open("http://localhost:3301", "_blank"); close(); }, keywords: ["signoz", "monitoring", "metrics", "traces", "logs", "observability", "otel"] },
        { id: "ext-otel", label: "OTel Collector", description: "OpenTelemetry OTLP endpoint :4318", group: "External Tools", icon: CmdIcons.external, action: () => { window.open("http://localhost:4318", "_blank"); close(); }, keywords: ["otel", "opentelemetry", "collector", "otlp", "metrics"] },
    ], [theme, toggleTheme, router, close]);

    /* ── Filtered & grouped results ───────────────────────────────────────── */
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

    /* ── Keyboard shortcut to open ────────────────────────────────────────── */
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

    /* ── Focus input on open ──────────────────────────────────────────────── */
    useEffect(() => {
        if (open) {
            requestAnimationFrame(() => inputRef.current?.focus());
        }
    }, [open]);

    /* ── Keep active item in view ─────────────────────────────────────────── */
    useEffect(() => {
        const el = listRef.current?.querySelector(`[data-index="${activeIndex}"]`);
        el?.scrollIntoView({ block: "nearest" });
    }, [activeIndex]);

    /* ── Keyboard navigation inside palette ───────────────────────────────── */
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "ArrowDown") {
            e.preventDefault();
            setActiveIndex((i) => (i + 1) % filtered.length);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActiveIndex((i) => (i - 1 + filtered.length) % filtered.length);
        } else if (e.key === "Enter") {
            e.preventDefault();
            filtered[activeIndex]?.action();
        }
    };

    /* ── Reset index on query change ──────────────────────────────────────── */
    useEffect(() => {
        setActiveIndex(0);
    }, [query]);

    if (!open) return null;

    let flatIndex = -1;

    return (
        <div className="cmd-overlay" onClick={close}>
            <div className="cmd-palette" onClick={(e) => e.stopPropagation()} onKeyDown={handleKeyDown}>
                {/* Search input */}
                <div className="cmd-input-wrap">
                    <span className="cmd-search-icon">{CmdIcons.search}</span>
                    <input
                        ref={inputRef}
                        className="cmd-input"
                        placeholder="Type a command or search..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        spellCheck={false}
                        autoComplete="off"
                    />
                    <kbd className="cmd-kbd">ESC</kbd>
                </div>

                {/* Results */}
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
                                            {idx === activeIndex && <span className="cmd-enter-hint">Enter &crarr;</span>}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="cmd-footer">
                    <span className="cmd-footer-hint">
                        <kbd>&uarr;</kbd><kbd>&darr;</kbd> navigate
                    </span>
                    <span className="cmd-footer-hint">
                        <kbd>Enter</kbd> select
                    </span>
                    <span className="cmd-footer-hint">
                        <kbd>Esc</kbd> close
                    </span>
                </div>
            </div>
        </div>
    );
}
