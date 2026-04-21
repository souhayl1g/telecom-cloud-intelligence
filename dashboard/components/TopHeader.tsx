"use client";
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePathname } from 'next/navigation';
import ThemeToggle from './ThemeToggle';
import LiveIndicator from './LiveIndicator';
import AICopilotIcon from './AICopilotIcon';

const pageTitles: Record<string, { title: string; subtitle: string }> = {
    '/overview': { title: 'Overview', subtitle: 'Platform intelligence overview' },
    '/anomalies': { title: 'Anomalies', subtitle: 'OSS & BSS anomaly detection' },
    '/sla-risk': { title: 'SLA Risk', subtitle: 'Breach probability & risk scores' },
    '/correlations': { title: 'Correlations', subtitle: 'OSS-BSS correlation explorer' },
    '/intelligence': { title: 'AI Intelligence', subtitle: 'Intelligence hub & insights' },
    '/predictive': { title: 'Forecast', subtitle: 'Predictive analytics & trends' },
    '/topology': { title: 'Topology', subtitle: 'Network topology view' },
    '/capacity': { title: 'Capacity', subtitle: 'Capacity planning & metrics' },
    '/data-warehouse': { title: 'Data Warehouse', subtitle: 'DWH explorer & catalog' },
    '/pipeline-runs': { title: 'Pipelines', subtitle: 'Pipeline execution history' },
    '/ops-metrics': { title: 'Health', subtitle: 'Operational health metrics' },
    '/model-evaluation': { title: 'Models', subtitle: 'ML model evaluation & metrics' },
    '/l4-agent': { title: 'L4 Agent', subtitle: 'ADN autonomous operations' },
};

export default function TopHeader() {
    const pathname = usePathname();
    const [now, setNow] = useState<string>('');
    const [searchOpen, setSearchOpen] = useState(false);

    const pageInfo = pageTitles[pathname] ?? { title: 'Operations', subtitle: 'Cloud Intelligence Platform' };

    useEffect(() => {
        const update = () => {
            const d = new Date();
            setNow(d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }));
        };
        update();
        const id = setInterval(update, 60000);
        return () => clearInterval(id);
    }, []);

    return (
        <header className="top-header">
            {/* Left: Page Title */}
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
            </div>

            {/* Center: Search */}
            <div className="top-header-center">
                <button
                    className="top-header-search"
                    onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))}
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <span>Search anything...</span>
                    <kbd>Ctrl K</kbd>
                </button>
            </div>

            {/* Right: Actions */}
            <div className="top-header-right">
                <AICopilotIcon />
                <div className="top-header-divider" />
                <span className="top-header-date">{now}</span>
                <div className="top-header-divider" />

                {/* Notification Bell */}
                <button className="top-header-icon-btn" title="Notifications">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                    </svg>
                    <span className="top-header-notification-dot" />
                </button>

                {/* MinIO Link */}
                <a href="http://localhost:9001" target="_blank" rel="noreferrer" className="top-header-icon-btn" title="MinIO Console">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                    </svg>
                </a>

                <div className="top-header-divider" />
                <ThemeToggle />
                <LiveIndicator />
            </div>
        </header>
    );
}
