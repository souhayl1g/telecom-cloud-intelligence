"use client";
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { formatTunisDate } from '../lib/time';
import ThemeToggle from './ThemeToggle';
import LiveIndicator from './LiveIndicator';
import NotificationPanel from './NotificationPanel';

const pageTitles: Record<string, { title: string; subtitle: string }> = {
    '/overview':         { title: 'Overview',       subtitle: 'Platform intelligence overview' },
    '/vae-anomalies':    { title: 'VAE OSS',         subtitle: 'Experience anomaly detection' },
    '/correlations':     { title: 'Correlations',    subtitle: 'OSS-CEM correlation explorer' },
    '/granger-causality': { title: 'Granger Causality', subtitle: 'Temporal causality analysis' },
    '/intelligence':     { title: 'AI Intelligence', subtitle: 'Intelligence hub & insights' },
    '/predictive':       { title: 'Forecast',        subtitle: 'Predictive analytics & trends' },
    '/capacity':         { title: 'Capacity',        subtitle: 'Capacity planning & metrics' },
    '/data-warehouse':   { title: 'Data Warehouse',  subtitle: 'DWH explorer & catalog' },
    '/pipeline-runs':    { title: 'Pipelines',       subtitle: 'Pipeline execution history' },
    '/ops-metrics':      { title: 'Health',          subtitle: 'Operational health metrics' },
    '/model-evaluation': { title: 'Models',          subtitle: 'ML model evaluation & metrics' },
    '/cem-scores':       { title: 'CEM Scores',      subtitle: 'Customer experience management' },
    '/rat-underservice': { title: 'RAT Analysis',    subtitle: 'Radio access technology underservice' },
    '/l4-agent':         { title: 'L4 Agent',        subtitle: 'ADN autonomous operations' },
};

export default function TopHeader() {
    const pathname = usePathname();
    const [now, setNow] = useState<string>('');

    const pageInfo = pageTitles[pathname] ?? { title: 'Operations', subtitle: 'NeXo Platform' };

    useEffect(() => {
        const update = () => {
            setNow(formatTunisDate(new Date().toISOString()));
        };
        update();
        const id = setInterval(update, 60000);
        return () => clearInterval(id);
    }, []);

    return (
        <header className="top-header">
            {/* Left: Page Title + OSS∩CEM Badge */}
            <div className="top-header-left">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={pathname}
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 8 }}
                        transition={{ duration: 0.25 }}
                        className="top-header-title-group"
                    >
                        <h1 className="top-header-title">{pageInfo.title}</h1>
                        <span className="top-header-subtitle">{pageInfo.subtitle}</span>
                    </motion.div>
                </AnimatePresence>
                <span className="oss-bss-badge">OSS∩CEM</span>
            </div>

            {/* Center: Search */}
            <div className="top-header-center">
                <button
                    className="top-header-search"
                    onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))}
                >
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>search</span>
                    <span>Search anything...</span>
                    <kbd>Ctrl K</kbd>
                </button>
            </div>

            {/* Right: Actions */}
            <div className="top-header-right">
                <Link
                    href="/l4-agent"
                    className="deploy-ai-btn"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>precision_manufacturing</span>
                    <span>Deploy AI</span>
                </Link>
                <div className="top-header-divider" />
                <span className="top-header-date">{now}</span>
                <div className="top-header-divider" />

                {/* Live notifications */}
                <NotificationPanel />

                <div className="top-header-divider" />
                <ThemeToggle />
                <LiveIndicator />
            </div>
        </header>
    );
}
