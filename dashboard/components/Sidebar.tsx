"use client";
import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/* ── Navigation Structure ─────────────────────────────────────────────── */
interface NavItem {
    href: string;
    label: string;
    icon: React.ReactNode;
    badge?: string;
}

interface NavSection {
    title: string;
    items: NavItem[];
}

const navSections: NavSection[] = [
    {
        title: 'Main',
        items: [
            {
                href: '/overview', label: 'Dashboard',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></svg>,
            },
            {
                href: '/anomalies', label: 'Anomalies',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>,
            },
            {
                href: '/sla-risk', label: 'SLA Risk',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
            },
            {
                href: '/correlations', label: 'Correlations',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" /></svg>,
            },
        ],
    },
    {
        title: 'Intelligence',
        items: [
            {
                href: '/intelligence', label: 'AI Hub',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" /><line x1="9" y1="21" x2="15" y2="21" /></svg>,
            },
            {
                href: '/predictive', label: 'Forecast',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>,
            },
            {
                href: '/model-evaluation', label: 'Models',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20V10" /><path d="M18 20V4" /><path d="M6 20v-4" /></svg>,
            },
        ],
    },
    {
        title: 'Infrastructure',
        items: [
            {
                href: '/topology', label: 'Topology',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><circle cx="19" cy="5" r="2" /><circle cx="5" cy="5" r="2" /><circle cx="19" cy="19" r="2" /><circle cx="5" cy="19" r="2" /><line x1="14" y1="10" x2="17.5" y2="6.5" /><line x1="10" y1="10" x2="6.5" y2="6.5" /><line x1="14" y1="14" x2="17.5" y2="17.5" /><line x1="10" y1="14" x2="6.5" y2="17.5" /></svg>,
            },
            {
                href: '/capacity', label: 'Capacity',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>,
            },
            {
                href: '/pipeline-runs', label: 'Pipelines',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="13 17 18 12 13 7" /><polyline points="6 17 11 12 6 7" /></svg>,
            },
            {
                href: '/ops-metrics', label: 'Health',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>,
            },
        ],
    },
    {
        title: 'Data',
        items: [
            {
                href: '/data-warehouse', label: 'Warehouse',
                icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>,
            },
        ],
    },
];

/* ── Sidebar Animation Variants ───────────────────────────────────────── */
const sidebarVariants = {
    expanded: { width: 260 },
    collapsed: { width: 72 },
};

const itemVariants = {
    hidden: { opacity: 0, x: -8 },
    visible: (i: number) => ({
        opacity: 1,
        x: 0,
        transition: { delay: i * 0.03, duration: 0.3, ease: [0.4, 0, 0.2, 1] as const },
    }),
};

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [collapsed, setCollapsed] = useState(false);
    const [hoveredItem, setHoveredItem] = useState<string | null>(null);

    // Persist sidebar state
    useEffect(() => {
        const saved = localStorage.getItem('sidebar-collapsed');
        if (saved === 'true') setCollapsed(true);
    }, []);

    const toggleCollapsed = () => {
        const next = !collapsed;
        setCollapsed(next);
        localStorage.setItem('sidebar-collapsed', String(next));
    };

    const handleLogout = async () => {
        await fetch('/api/logout', { method: 'POST' });
        router.push('/login');
        router.refresh();
    };

    let itemIndex = 0;

    return (
        <motion.aside
            className="sidebar"
            variants={sidebarVariants}
            animate={collapsed ? 'collapsed' : 'expanded'}
            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        >
            {/* ── Logo ────────────────────────────────── */}
            <div className="sidebar-header">
                <Link href="/overview" className="sidebar-logo">
                    <div className="sidebar-logo-icon">
                        <Image src="/images/logo.svg" alt="Logo" width={32} height={32} priority />
                    </div>
                    <AnimatePresence>
                        {!collapsed && (
                            <motion.div
                                className="sidebar-logo-text"
                                initial={{ opacity: 0, width: 0 }}
                                animate={{ opacity: 1, width: 'auto' }}
                                exit={{ opacity: 0, width: 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <span className="sidebar-brand">
                                    <span className="sidebar-brand-accent">Cloud</span> Intel
                                </span>
                                <span className="sidebar-brand-sub">ADN Operations</span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </Link>
                <button className="sidebar-toggle" onClick={toggleCollapsed} title={collapsed ? 'Expand' : 'Collapse'}>
                    <motion.svg
                        width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                        animate={{ rotate: collapsed ? 180 : 0 }}
                        transition={{ duration: 0.3 }}
                    >
                        <polyline points="11 17 6 12 11 7" />
                        <polyline points="18 17 13 12 18 7" />
                    </motion.svg>
                </button>
            </div>

            {/* ── Navigation ──────────────────────────── */}
            <nav className="sidebar-nav">
                {navSections.map((section) => (
                    <div key={section.title} className="sidebar-section">
                        <AnimatePresence>
                            {!collapsed && (
                                <motion.div
                                    className="sidebar-section-title"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 0.15 }}
                                >
                                    {section.title}
                                </motion.div>
                            )}
                        </AnimatePresence>
                        {section.items.map((item) => {
                            const active = pathname === item.href || pathname.startsWith(item.href + '/');
                            const idx = itemIndex++;
                            return (
                                <motion.div
                                    key={item.href}
                                    custom={idx}
                                    variants={itemVariants}
                                    initial="hidden"
                                    animate="visible"
                                >
                                    <Link
                                        href={item.href}
                                        className={`sidebar-item ${active ? 'sidebar-item-active' : ''}`}
                                        onMouseEnter={() => setHoveredItem(item.href)}
                                        onMouseLeave={() => setHoveredItem(null)}
                                        title={collapsed ? item.label : undefined}
                                    >
                                        {active && (
                                            <motion.div
                                                className="sidebar-item-indicator"
                                                layoutId="sidebar-indicator"
                                                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                                            />
                                        )}
                                        <span className="sidebar-item-icon">{item.icon}</span>
                                        <AnimatePresence>
                                            {!collapsed && (
                                                <motion.span
                                                    className="sidebar-item-label"
                                                    initial={{ opacity: 0, width: 0 }}
                                                    animate={{ opacity: 1, width: 'auto' }}
                                                    exit={{ opacity: 0, width: 0 }}
                                                    transition={{ duration: 0.2 }}
                                                >
                                                    {item.label}
                                                </motion.span>
                                            )}
                                        </AnimatePresence>
                                        {item.badge && !collapsed && (
                                            <span className="sidebar-item-badge">{item.badge}</span>
                                        )}
                                    </Link>
                                    {/* Tooltip when collapsed */}
                                    {collapsed && hoveredItem === item.href && (
                                        <motion.div
                                            className="sidebar-tooltip"
                                            initial={{ opacity: 0, x: -4 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0 }}
                                        >
                                            {item.label}
                                        </motion.div>
                                    )}
                                </motion.div>
                            );
                        })}
                    </div>
                ))}
            </nav>

            {/* ── L4 Agent CTA ────────────────────────── */}
            <div className="sidebar-agent-section">
                <Link
                    href="/l4-agent"
                    className={`sidebar-agent-cta ${pathname.startsWith('/l4-agent') ? 'sidebar-agent-active' : ''}`}
                >
                    <div className="sidebar-agent-pulse" />
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /><circle cx="12" cy="16" r="1" />
                    </svg>
                    <AnimatePresence>
                        {!collapsed && (
                            <motion.div
                                className="sidebar-agent-text"
                                initial={{ opacity: 0, width: 0 }}
                                animate={{ opacity: 1, width: 'auto' }}
                                exit={{ opacity: 0, width: 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <span className="sidebar-agent-label">L4 Agent</span>
                                <span className="sidebar-agent-status">Online</span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </Link>
            </div>

            {/* ── Footer ──────────────────────────────── */}
            <div className="sidebar-footer">
                <div className="sidebar-footer-divider" />
                <div className="sidebar-footer-actions">
                    <button className="sidebar-footer-btn" onClick={handleLogout} title="Sign Out">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
                        </svg>
                        <AnimatePresence>
                            {!collapsed && (
                                <motion.span
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 0.15 }}
                                >
                                    Sign Out
                                </motion.span>
                            )}
                        </AnimatePresence>
                    </button>
                </div>
            </div>
        </motion.aside>
    );
}
