"use client";
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

const sections = [
    {
        label: 'Intelligence',
        items: [
            { href: '/overview', label: 'Overview', icon: '\u2302' },
            { href: '/sla-risk', label: 'SLA Risk', icon: '\u26A0' },
            { href: '/anomalies', label: 'Anomalies', icon: '\u2687' },
            { href: '/correlations', label: 'OSS\u2194BSS Correlation', icon: '\u2194' },
        ],
    },
    {
        label: 'Operations',
        items: [
            { href: '/pipeline-runs', label: 'Pipeline Runs', icon: '\u25B6' },
            { href: '/ops-metrics', label: 'Platform Health', icon: '\u2661' },
        ],
    },
];

export default function Nav() {
    const pathname = usePathname();
    const router = useRouter();

    const handleLogout = async () => {
        await fetch('/api/logout', { method: 'POST' });
        router.push('/login');
        router.refresh();
    };

    return (
        <aside className="nav">
            <div className="nav-brand">
                <div className="logo">AI Operations Agent</div>
                <div className="logo-sub">Telecom Cloud Intelligence</div>
            </div>

            <div style={{ flex: 1 }}>
                {sections.map((section) => (
                    <div key={section.label}>
                        <div className="nav-section-label">{section.label}</div>
                        {section.items.map((item) => {
                            const active = pathname === item.href || pathname.startsWith(item.href + '/');
                            return (
                                <Link key={item.href} href={item.href} className={active ? 'active' : ''}>
                                    <span className="nav-icon">{item.icon}</span>
                                    {item.label}
                                </Link>
                            );
                        })}
                    </div>
                ))}
            </div>

            <div className="nav-footer">
                <button
                    onClick={handleLogout}
                    style={{
                        width: '100%',
                        padding: '10px 14px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        color: 'var(--text-muted)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        fontWeight: 500,
                        textAlign: 'center',
                        transition: 'all 0.2s',
                        fontSize: '13px',
                        fontFamily: 'inherit',
                    }}
                    onMouseOver={(e) => {
                        e.currentTarget.style.color = 'var(--text-primary)';
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                    }}
                    onMouseOut={(e) => {
                        e.currentTarget.style.color = 'var(--text-muted)';
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                    }}
                >
                    Sign Out
                </button>
            </div>
        </aside>
    );
}
