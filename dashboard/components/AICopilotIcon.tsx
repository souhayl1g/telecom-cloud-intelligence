"use client";
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AICopilotIcon() {
    const [expanded, setExpanded] = useState(false);
    const router = useRouter();
    const wrapRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!expanded) return;
        const handler = (e: MouseEvent) => {
            if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
                setExpanded(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [expanded]);

    const navigate = (path: string) => {
        setExpanded(false);
        router.push(path);
    };

    return (
        <div ref={wrapRef} className="l4-pill-wrap">
            <button
                className={`l4-pill ${expanded ? 'l4-pill-open' : ''}`}
                onClick={() => setExpanded(!expanded)}
                title="L4 Autonomous Agent"
            >
                <span className="l4-pill-pulse" />
                <svg className="l4-pill-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0-3 3v1a3 3 0 0 0-3 3 3 3 0 0 0 3 3v1a3 3 0 0 0 3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 3-3v-1a3 3 0 0 0 3-3 3 3 0 0 0-3-3V9a3 3 0 0 0-3-3V5a3 3 0 0 0-3-3z" />
                    <path d="M12 8v8M8 12h8" />
                </svg>
                <span className="l4-pill-label">L4 Agent</span>
                <span className="l4-pill-badge">ADN</span>
            </button>

            {expanded && (
                <div className="l4-pill-menu">
                    <div className="l4-pill-menu-header">
                        <div className="l4-pill-menu-dot" />
                        <span>Autonomous Operations</span>
                        <span className="badge badge-success" style={{ fontSize: 9, padding: '1px 6px' }}>LIVE</span>
                    </div>
                    <button className="l4-pill-menu-item" onClick={() => navigate('/l4-agent')}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                        Open Agent Workspace
                    </button>
                    <button className="l4-pill-menu-item" onClick={() => navigate('/model-evaluation')}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
                        Model Evaluation
                    </button>
                    <button className="l4-pill-menu-item" onClick={() => navigate('/intelligence')}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" /><line x1="9" y1="21" x2="15" y2="21" /></svg>
                        Intelligence Hub
                    </button>
                    <div className="l4-pill-menu-footer">
                        ADN L4 · Qwen2.5 7B · 30s cycle
                    </div>
                </div>
            )}
        </div>
    );
}
