"use client";
import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import LiveIndicator from './LiveIndicator';
import ThemeToggle from './ThemeToggle';

/* ── SVG Icon Components ─────────────────────────────────────────────────── */
const Icons = {
    overview: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
    ),
    correlations: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
    ),
    pipelines: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="13 17 18 12 13 7" /><polyline points="6 17 11 12 6 7" />
        </svg>
    ),
    health: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
    ),
    agent: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
            <circle cx="12" cy="16" r="1" />
        </svg>
    ),
    minio: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
    ),
    cemScores: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
        </svg>
    ),
    ratUnderservice: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 20h20" /><path d="M5 20v-5" /><path d="M9 20v-8" /><path d="M13 20V9" /><path d="M17 20V5" /><path d="M21 20V2" />
        </svg>
    ),
    vaeAnomalies: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
    ),
    dwh: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" /><path d="M18 17V9" /><path d="M13 17V5" /><path d="M8 17v-3" />
        </svg>
    ),
    intelligence: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" />
            <line x1="9" y1="21" x2="15" y2="21" />
        </svg>
    ),
    logout: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
        </svg>
    ),
};

interface NavItem {
    href: string;
    label: string;
    icon: React.ReactNode;
}

const navItems: NavItem[] = [
    { href: '/overview', label: 'Overview', icon: Icons.overview },
    { href: '/correlations', label: 'Correlations', icon: Icons.correlations },
    { href: '/granger-causality', label: 'Granger', icon: Icons.pipelines },
    { href: '/intelligence', label: 'Intelligence', icon: Icons.intelligence },
    { href: '/predictive', label: 'Forecast', icon: Icons.health },
    { href: '/topology', label: 'Topology', icon: Icons.correlations },
    { href: '/capacity', label: 'Capacity', icon: Icons.health },
    { href: '/data-warehouse', label: 'DWH', icon: Icons.dwh },
    { href: '/pipeline-runs', label: 'Pipelines', icon: Icons.pipelines },
    { href: '/ops-metrics', label: 'Health', icon: Icons.health },
    { href: '/model-evaluation', label: 'Models', icon: Icons.intelligence },
    { href: '/cem-scores', label: 'CEM', icon: Icons.cemScores },
    { href: '/rat-underservice', label: 'RAT', icon: Icons.ratUnderservice },
    { href: '/vae-anomalies', label: 'VAE', icon: Icons.vaeAnomalies },
];

export default function TopNav() {
    const pathname = usePathname();
    const router = useRouter();

    const handleLogout = async () => {
        await fetch('/api/logout', { method: 'POST' });
        router.push('/login');
        router.refresh();
    };

    const agentActive = pathname === '/l4-agent' || pathname.startsWith('/l4-agent/');

    return (
        <header className="topnav">
            <div className="topnav-brand">
                <Link href="/overview" className="logo-group" style={{ textDecoration: 'none' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Image src="/images/logo.svg" alt="NeXo" width={28} height={28} priority />
                        <div>
                            <span className="logo-sparkly">
                                <span className="hw-red">Cloud</span> Intelligence
                            </span>
                            <div className="logo-badge">ADN Operations</div>
                        </div>
                    </div>
                </Link>
            </div>

            <nav className="topnav-links">
                {navItems.map((item) => {
                    const active = pathname === item.href || pathname.startsWith(item.href + '/');
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`topnav-item ${active ? 'active' : ''}`}
                        >
                            <span className="topnav-icon">{item.icon}</span>
                            {item.label}
                        </Link>
                    );
                })}

                <div className="topnav-separator" />

                <Link
                    href="/l4-agent"
                    className={`topnav-agent-cta ${agentActive ? 'active' : ''}`}
                >
                    <span className="topnav-agent-pulse" />
                    <span className="topnav-icon">{Icons.agent}</span>
                    L4 Agent
                </Link>
            </nav>

            <div className="topnav-actions">
                <a href="http://localhost:19999" target="_blank" rel="noreferrer" className="pill-btn" title="Netdata — Real-time system & container monitoring">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                    </svg> Netdata
                </a>
                <a href="http://localhost:3000" target="_blank" rel="noreferrer" className="pill-btn" title="Grafana — Dashboards & visualization">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18" /><path d="M9 21V9" />
                    </svg> Grafana
                </a>
                <a href="http://localhost:16686" target="_blank" rel="noreferrer" className="pill-btn" title="Jaeger — Distributed trace explorer">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                    </svg> Jaeger
                </a>
                <a href="http://localhost:9001" target="_blank" rel="noreferrer" className="pill-btn" title="MinIO Object Storage Console">
                    {Icons.minio} MinIO
                </a>
                <div className="vertical-divider"></div>
                <button
                    className="cmd-trigger-btn"
                    onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))}
                    title="Command Palette (Ctrl+K)"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <span className="cmd-trigger-label">Search</span>
                    <kbd className="cmd-trigger-kbd">Ctrl K</kbd>
                </button>
                <div className="vertical-divider"></div>
                <ThemeToggle />
                <LiveIndicator />
                <button onClick={handleLogout} className="logout-icon-btn" title="Sign Out">
                    {Icons.logout}
                </button>
            </div>
        </header>
    );
}
