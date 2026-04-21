"use client";
import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { useRefresh } from './RefreshContext';

interface PageHeroValue {
    icon?: ReactNode;
    text: string;
}

interface PageHeroProps {
    eyebrow: string;           // e.g. "CEM · OSS+BSS convergence"
    title: string;             // service name, short and clear
    description: string;       // 1-2 sentence "what this page gives you"
    values?: PageHeroValue[];  // concrete outcomes for the user
    right?: ReactNode;         // optional custom right slot (KPI, status)
    showBrand?: boolean;       // show TT × Huawei chip (default: true)
    showRefresh?: boolean;     // show silent refresh badge (default: true)
}

const CheckIcon = (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
    </svg>
);

export default function PageHero({ eyebrow, title, description, values, right, showBrand = true, showRefresh = true }: PageHeroProps) {
    const { lastRefreshed, refreshNow, paused, setPaused, intervalMs } = useRefresh();

    const secondsSince = lastRefreshed ? Math.floor((Date.now() - lastRefreshed.getTime()) / 1000) : null;
    const nextInSec = Math.max(0, Math.round(intervalMs / 1000) - (secondsSince ?? 0));

    return (
        <motion.section
            className="page-hero"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        >
            <div className="page-hero-main">
                <div className="page-hero-eyebrow">
                    <span className="page-hero-eyebrow-dot" />
                    {eyebrow}
                </div>
                <h1 className="page-hero-title">{title}</h1>
                <p className="page-hero-description">{description}</p>
                {values && values.length > 0 && (
                    <div className="page-hero-value">
                        {values.map((v, i) => (
                            <div className="page-hero-value-item" key={i}>
                                {v.icon ?? CheckIcon}
                                <span>{v.text}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            <div className="page-hero-side">
                {showBrand && (
                    <div className="brand-dual" title="Tunisie Telecom operating on Huawei Cloud Stack">
                        <span className="brand-dual-tt">
                            <span className="brand-dual-dot" style={{ background: 'var(--brand-tt)' }} />
                            TT
                        </span>
                        <span className="brand-dual-x">on</span>
                        <span className="brand-dual-huawei">
                            <span className="brand-dual-dot" style={{ background: 'var(--brand-huawei)' }} />
                            Huawei&nbsp;HCS
                        </span>
                    </div>
                )}
                {showRefresh && (
                    <button
                        type="button"
                        onClick={() => paused ? setPaused(false) : refreshNow()}
                        className="refresh-badge"
                        title={paused ? 'Resume auto-refresh' : `Click to refresh now (auto: every ${Math.round(intervalMs / 1000)}s)`}
                        style={{ cursor: 'pointer', border: 'none' }}
                    >
                        <span className="refresh-badge-dot" style={{ background: paused ? 'var(--color-warning)' : 'var(--color-success)' }} />
                        {paused ? 'Paused' : lastRefreshed ? `Updated ${secondsSince}s ago · next in ${nextInSec}s` : 'Live'}
                    </button>
                )}
                {right}
            </div>
        </motion.section>
    );
}
