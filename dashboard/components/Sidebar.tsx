"use client";
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface NavItem {
    href: string;
    label: string;
    icon: string; // Material Symbol name
    badge?: string;
}

interface NavSection {
    title: string;
    items: NavItem[];
}

const navSections: NavSection[] = [
    {
        title: 'Network',
        items: [
            { href: '/overview',      label: 'Overview',     icon: 'dashboard' },
            { href: '/anomalies',     label: 'Anomalies',    icon: 'warning' },
            { href: '/vae-anomalies', label: 'VAE OSS',    icon: 'science' },
            { href: '/sla-risk',      label: 'SLA Risk',     icon: 'timer' },
            { href: '/correlations',  label: 'Correlations', icon: 'hub' },
        ],
    },
    {
        title: 'Intelligence',
        items: [
            { href: '/intelligence',     label: 'AI Hub',    icon: 'smart_toy' },
            { href: '/predictive',       label: 'Forecast',  icon: 'trending_up' },
            { href: '/model-evaluation', label: 'Models',    icon: 'model_training' },
            { href: '/cem-scores',       label: 'CEM',       icon: 'analytics' },
            { href: '/rat-underservice', label: 'RAT',       icon: 'signal_cellular_alt' },
        ],
    },
    {
        title: 'Infrastructure',
        items: [
            { href: '/topology',      label: 'Topology',  icon: 'device_hub' },
            { href: '/capacity',      label: 'Capacity',  icon: 'storage' },
            { href: '/pipeline-runs', label: 'Pipelines', icon: 'account_tree' },
            { href: '/ops-metrics',   label: 'Health',    icon: 'monitor_heart' },
        ],
    },
    {
        title: 'Data',
        items: [
            { href: '/data-warehouse', label: 'Warehouse', icon: 'database' },
        ],
    },
];

const sidebarVariants = {
    expanded:  { width: 256 },
    collapsed: { width: 72 },
};

const itemVariants = {
    hidden:  { opacity: 0, x: -8 },
    visible: (i: number) => ({
        opacity: 1, x: 0,
        transition: { delay: i * 0.03, duration: 0.3, ease: [0.4, 0, 0.2, 1] as const },
    }),
};

export default function Sidebar() {
    const pathname = usePathname();
    const router   = useRouter();
    const [collapsed,    setCollapsed]    = useState(false);
    const [hoveredItem,  setHoveredItem]  = useState<string | null>(null);

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
            {/* ── Logo / Brand ─────────────────────────── */}
            <div className="sidebar-header">
                <Link href="/overview" className="sidebar-logo">
                    <div className="sidebar-logo-icon">
                        <span className="material-symbols-outlined" style={{ fontSize: 20, color: '#dc2626' }}>
                            bolt
                        </span>
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
                                <span className="sidebar-brand">NeXo Intelligence</span>
                                <span className="sidebar-brand-sub">ADN Operations</span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </Link>
                <button
                    className="sidebar-toggle"
                    onClick={toggleCollapsed}
                    title={collapsed ? 'Expand' : 'Collapse'}
                >
                    <motion.span
                        className="material-symbols-outlined"
                        style={{ fontSize: 16 }}
                        animate={{ rotate: collapsed ? 180 : 0 }}
                        transition={{ duration: 0.3 }}
                    >
                        chevron_left
                    </motion.span>
                </button>
            </div>

            {/* ── User Profile ─────────────────────────── */}
            <AnimatePresence>
                {!collapsed && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        style={{
                            padding: '8px 16px 12px',
                            borderBottom: '1px solid rgba(255,255,255,0.05)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                            flexShrink: 0,
                        }}
                    >
                        <div style={{
                            width: 32, height: 32, borderRadius: '50%',
                            background: 'rgba(255,255,255,0.08)',
                            border: '1px solid rgba(255,255,255,0.10)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            flexShrink: 0,
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#ef4444' }}>
                                person
                            </span>
                        </div>
                        <div style={{ overflow: 'hidden' }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#E8ECF1', fontFamily: "'Fira Sans', sans-serif", whiteSpace: 'nowrap' }}>
                                NOC Operator
                            </div>
                            <div style={{ fontSize: 10, color: '#546478', fontFamily: "'Fira Sans', sans-serif" }}>
                                Active Session
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Navigation ───────────────────────────── */}
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
                                    style={{ position: 'relative' }}
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
                                        <span className="sidebar-item-icon">
                                            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                                                {item.icon}
                                            </span>
                                        </span>
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

            {/* ── L4 Agent CTA ─────────────────────────── */}
            <div className="sidebar-agent-section">
                <Link
                    href="/l4-agent"
                    className={`sidebar-agent-cta ${pathname.startsWith('/l4-agent') ? 'sidebar-agent-active' : ''}`}
                >
                    <div className="sidebar-agent-pulse" />
                    <span className="material-symbols-outlined" style={{ fontSize: 18, flexShrink: 0 }}>
                        precision_manufacturing
                    </span>
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

            {/* ── Footer ───────────────────────────────── */}
            <div className="sidebar-footer">
                <div className="sidebar-footer-divider" />
                <div className="sidebar-footer-actions">
                    <button className="sidebar-footer-btn" onClick={handleLogout} title="Sign Out">
                        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>logout</span>
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
