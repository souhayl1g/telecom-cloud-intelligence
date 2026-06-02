"use client";
import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface NavItem {
    href: string;
    label: string;
    icon: string;
    badge?: string;
    dim?: boolean;
}

interface NavSection {
    title: string;
    items: NavItem[];
    collapsible?: boolean;
    defaultCollapsed?: boolean;
}

// Story-arc order: pain → hero → proof → evidence → close-loop → depth.
// Each section maps to a beat in the defense narrative.
const navSections: NavSection[] = [
    {
        title: 'Start Here',
        items: [
            { href: '/overview', label: 'Overview', icon: 'dashboard' },
        ],
    },
    {
        title: 'Autonomy',
        items: [
            { href: '/l4-agent', label: 'L4 Agent', icon: 'precision_manufacturing', badge: 'L4' },
        ],
    },
    {
        title: 'Convergence',
        items: [
            { href: '/granger-causality', label: 'Granger', icon: 'account_tree' },
            { href: '/correlations',      label: 'Correlations', icon: 'hub', dim: true },
        ],
    },
    {
        title: 'ML Models',
        items: [
            { href: '/cem-scores',       label: 'CEM Scores',  icon: 'analytics' },
            { href: '/vae-anomalies',    label: 'VAE Anomalies', icon: 'science' },
            { href: '/rat-underservice', label: 'RAT Gap',     icon: 'signal_cellular_alt' },
        ],
    },
    {
        title: 'Actuation',
        items: [
            { href: '/tickets',       label: 'Tickets',       icon: 'confirmation_number' },
            { href: '/notifications', label: 'Notifications', icon: 'notifications_active', dim: true },
            { href: '/interventions', label: 'Interventions', icon: 'shield_person',         dim: true },
            { href: '/reports',       label: 'Reports',       icon: 'picture_as_pdf',        dim: true },
        ],
    },
    {
        title: 'More',
        collapsible: true,
        defaultCollapsed: true,
        items: [
            { href: '/predictive',       label: 'Forecast',  icon: 'trending_up' },
            { href: '/capacity',         label: 'Capacity',  icon: 'storage' },
            { href: '/intelligence',     label: 'AI Hub',    icon: 'smart_toy' },
            { href: '/model-evaluation', label: 'Models',    icon: 'model_training' },
            { href: '/pipeline-runs',    label: 'Pipelines', icon: 'rocket_launch' },
            { href: '/ops-metrics',      label: 'Health',    icon: 'monitor_heart' },
            { href: '/data-warehouse',   label: 'Warehouse', icon: 'database' },
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
        transition: { delay: i * 0.025, duration: 0.25, ease: [0.4, 0, 0.2, 1] as const },
    }),
};

export default function Sidebar() {
    const pathname = usePathname();
    const router   = useRouter();
    // Default collapsed = pro icon-rail (Linear/Vercel/Stripe style)
    const [collapsed,    setCollapsed]    = useState(true);
    const [hoveredItem,  setHoveredItem]  = useState<string | null>(null);
    const [openGroups,   setOpenGroups]   = useState<Record<string, boolean>>(() => {
        const m: Record<string, boolean> = {};
        navSections.forEach(s => { m[s.title] = !s.defaultCollapsed; });
        return m;
    });

    useEffect(() => {
        const saved = localStorage.getItem('sidebar-collapsed');
        if (saved !== null) setCollapsed(saved === 'true');
        try {
            const g = localStorage.getItem('sidebar-groups');
            if (g) setOpenGroups(prev => ({ ...prev, ...JSON.parse(g) }));
        } catch {}
    }, []);

    const toggleCollapsed = () => {
        const next = !collapsed;
        setCollapsed(next);
        localStorage.setItem('sidebar-collapsed', String(next));
    };

    const toggleGroup = (title: string) => {
        setOpenGroups(prev => {
            const next = { ...prev, [title]: !prev[title] };
            try { localStorage.setItem('sidebar-groups', JSON.stringify(next)); } catch {}
            return next;
        });
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
                    <div className="sidebar-logo-icon" style={{ padding: 2 }}>
                        <Image
                            src="/images/nexo-logo.png"
                            alt="NeXo"
                            width={28}
                            height={28}
                            style={{ objectFit: 'contain', borderRadius: 6 }}
                        />
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

            {/* ── Cmd+K hint ───────────────────────────── */}
            <AnimatePresence>
                {!collapsed && (
                    <motion.button
                        className="sidebar-cmdk-hint"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        onClick={() => {
                            window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>search</span>
                        <span>Quick command</span>
                        <kbd>⌘K</kbd>
                    </motion.button>
                )}
            </AnimatePresence>

            {/* ── Navigation ───────────────────────────── */}
            <nav className="sidebar-nav">
                {navSections.map((section) => {
                    const isOpen = openGroups[section.title] ?? !section.defaultCollapsed;
                    const showItems = !section.collapsible || isOpen || collapsed;
                    return (
                        <div key={section.title} className="sidebar-section">
                            <AnimatePresence>
                                {!collapsed && (
                                    <motion.div
                                        className={`sidebar-section-title ${section.collapsible ? 'sidebar-section-collapsible' : ''}`}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ duration: 0.15 }}
                                        onClick={section.collapsible ? () => toggleGroup(section.title) : undefined}
                                        style={section.collapsible ? { cursor: 'pointer' } : undefined}
                                    >
                                        <span>{section.title}</span>
                                        {section.collapsible && (
                                            <motion.span
                                                className="material-symbols-outlined"
                                                style={{ fontSize: 14, marginLeft: 'auto' }}
                                                animate={{ rotate: isOpen ? 0 : -90 }}
                                                transition={{ duration: 0.2 }}
                                            >
                                                expand_more
                                            </motion.span>
                                        )}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                            {showItems && section.items.map((item) => {
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
                                            className={`sidebar-item ${active ? 'sidebar-item-active' : ''} ${item.dim ? 'sidebar-item-dim' : ''}`}
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
                    );
                })}
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
