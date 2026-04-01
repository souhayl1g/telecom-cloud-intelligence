"use client";
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import LiveIndicator from './LiveIndicator';

/* ── SVG Icon Components ─────────────────────────────────────────────────── */
const Icons = {
    overview: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
    ),
    slaRisk: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
    ),
    anomalies: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
    ),
    correlations: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
    ),
    pipelines: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="13 17 18 12 13 7" /><polyline points="6 17 11 12 6 7" />
        </svg>
    ),
    health: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
    ),
    agent: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
    dwh: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" /><path d="M18 17V9" /><path d="M13 17V5" /><path d="M8 17v-3" />
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
    glow?: boolean;
}

const navItems: NavItem[] = [
    { href: '/overview', label: 'Overview', icon: Icons.overview },
    { href: '/sla-risk', label: 'SLA Risk', icon: Icons.slaRisk },
    { href: '/anomalies', label: 'Anomalies', icon: Icons.anomalies },
    { href: '/correlations', label: 'Correlations', icon: Icons.correlations },
    { href: '/pipeline-runs', label: 'Pipelines', icon: Icons.pipelines },
    { href: '/ops-metrics', label: 'Health', icon: Icons.health },
    { href: '/l4-agent', label: 'L4 Agent', icon: Icons.agent, glow: true },
];

export default function TopNav() {
    const pathname = usePathname();
    const router = useRouter();

    const handleLogout = async () => {
        await fetch('/api/logout', { method: 'POST' });
        router.push('/login');
        router.refresh();
    };

    return (
        <header className="topnav">
            <div className="topnav-brand">
                <div className="logo-group">
                    <span className="logo-sparkly">AI Operations Agent</span>
                    <div className="logo-badge">L4 Autonomous</div>
                </div>
            </div>

            <nav className="topnav-links">
                {navItems.map((item) => {
                    const active = pathname === item.href || pathname.startsWith(item.href + '/');
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`topnav-item ${active ? 'active' : ''} ${item.glow ? 'glow' : ''}`}
                        >
                            <span className="topnav-icon">{item.icon}</span>
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            <div className="topnav-actions">
                <div className="external-links">
                    <a href="http://localhost:9001" target="_blank" rel="noreferrer" className="pill-btn minio" title="MinIO Object Storage Console">
                        {Icons.minio} MinIO
                    </a>
                    <a href="http://localhost:3000" target="_blank" rel="noreferrer" className="pill-btn dwh" title="Grafana Data Warehouse Dashboard">
                        {Icons.dwh} DWH
                    </a>
                </div>
                <div className="vertical-divider"></div>
                <LiveIndicator />
                <button onClick={handleLogout} className="logout-btn">
                    {Icons.logout}
                    Sign Out
                </button>
            </div>
        </header>
    );
}
