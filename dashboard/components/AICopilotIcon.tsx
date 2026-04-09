"use client";
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AICopilotIcon() {
    const [expanded, setExpanded] = useState(false);
    const router = useRouter();
    const menuRef = useRef<HTMLDivElement>(null);

    // Close menu when clicking outside
    useEffect(() => {
        if (!expanded) return;
        const handler = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
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
        <div ref={menuRef} style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1000 }}>
            {/* Expanded Menu */}
            {expanded && (
                <div className="ai-copilot-menu" style={{ position: 'absolute', bottom: 62, right: 0 }}>
                    <div className="ai-copilot-menu-header">
                        <div className="ai-copilot-menu-dot" />
                        <span>NexOps AI Agent</span>
                        <span className="badge badge-success" style={{ fontSize: 8, padding: '1px 6px' }}>ACTIVE</span>
                    </div>
                    <button className="ai-copilot-menu-item" onClick={() => navigate('/l4-agent')}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                        Open Agent Chat
                    </button>
                    <button className="ai-copilot-menu-item" onClick={() => navigate('/model-evaluation')}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
                        Model Evaluation
                    </button>
                    <button className="ai-copilot-menu-item" onClick={() => navigate('/intelligence')}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" /><line x1="9" y1="21" x2="15" y2="21" /></svg>
                        Intelligence Hub
                    </button>
                    <div className="ai-copilot-menu-footer">
                        ADN L4 | Qwen2.5 7B | 120s cycle
                    </div>
                </div>
            )}

            {/* FAB Button */}
            <button
                className={`ai-copilot-fab ${expanded ? 'ai-copilot-fab-hover' : ''}`}
                onClick={() => setExpanded(!expanded)}
                style={{ border: 'none' }}
            >
                <div className="ai-copilot-pulse" />
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="11" width="18" height="10" rx="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    <circle cx="12" cy="16" r="1" />
                </svg>
            </button>
        </div>
    );
}
