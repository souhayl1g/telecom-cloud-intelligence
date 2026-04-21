import { ReactNode } from 'react';

interface PageInfoValue {
    icon?: ReactNode;
    text: string;
}

interface PageInfoBarProps {
    eyebrow?: string;
    description: string;
    values?: PageInfoValue[];
}

/**
 * Compact, collapsible "About this page" control.
 * Uses native <details>/<summary> so it works in server components without JS.
 * Renders as a tiny ℹ icon that expands an inline panel with the page rationale.
 */
export default function PageInfoBar({ eyebrow, description, values }: PageInfoBarProps) {
    return (
        <details className="page-info-bar">
            <summary className="page-info-trigger" title="About this page">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="16" x2="12" y2="12" />
                    <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                <span className="page-info-trigger-label">About</span>
            </summary>
            <div className="page-info-panel">
                {eyebrow && (
                    <div className="page-info-eyebrow">
                        <span className="page-info-eyebrow-dot" />
                        {eyebrow}
                    </div>
                )}
                <p className="page-info-desc">{description}</p>
                {values && values.length > 0 && (
                    <ul className="page-info-values">
                        {values.map((v, i) => (
                            <li key={i}>{v.text}</li>
                        ))}
                    </ul>
                )}
            </div>
        </details>
    );
}
