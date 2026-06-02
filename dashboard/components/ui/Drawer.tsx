"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

interface Props {
    open: boolean;
    onClose: () => void;
    title?: string;
    subtitle?: string;
    width?: number;
    children: React.ReactNode;
}

export default function Drawer({
    open,
    onClose,
    title,
    subtitle,
    width = 520,
    children,
}: Props) {
    useEffect(() => {
        if (!open) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        window.addEventListener("keydown", onKey);
        const prevOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        return () => {
            window.removeEventListener("keydown", onKey);
            document.body.style.overflow = prevOverflow;
        };
    }, [open, onClose]);

    if (!open) return null;

    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 1000,
                display: "flex",
                justifyContent: "flex-end",
            }}
        >
            <div
                onClick={onClose}
                style={{
                    position: "absolute",
                    inset: 0,
                    background: "rgba(0,0,0,0.55)",
                    backdropFilter: "blur(2px)",
                }}
            />
            <aside
                role="dialog"
                aria-modal="true"
                aria-label={title || "Detail panel"}
                style={{
                    position: "relative",
                    width: `min(${width}px, 95vw)`,
                    height: "100vh",
                    background: "var(--bg-elevated, #0f172a)",
                    borderLeft: "1px solid var(--border, #1e293b)",
                    boxShadow: "-12px 0 32px rgba(0,0,0,0.4)",
                    display: "flex",
                    flexDirection: "column",
                    animation: "drawerSlideIn 200ms cubic-bezier(0.16, 1, 0.3, 1)",
                }}
            >
                <header
                    style={{
                        padding: "14px 18px",
                        borderBottom: "1px solid var(--border, #1e293b)",
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 12,
                    }}
                >
                    <div style={{ flex: 1, minWidth: 0 }}>
                        {title && (
                            <div
                                style={{
                                    fontSize: 15,
                                    fontWeight: 700,
                                    color: "var(--text-primary, #e2e8f0)",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {title}
                            </div>
                        )}
                        {subtitle && (
                            <div
                                style={{
                                    fontSize: 11,
                                    color: "var(--text-muted, #64748b)",
                                    marginTop: 2,
                                }}
                            >
                                {subtitle}
                            </div>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="Close"
                        style={{
                            background: "transparent",
                            border: "1px solid var(--border, #1e293b)",
                            borderRadius: 6,
                            padding: 6,
                            cursor: "pointer",
                            color: "var(--text-muted, #64748b)",
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                        }}
                    >
                        <X size={14} />
                    </button>
                </header>
                <div
                    style={{
                        padding: "16px 18px",
                        overflowY: "auto",
                        flex: 1,
                        fontSize: 13,
                        color: "var(--text-primary, #e2e8f0)",
                    }}
                >
                    {children}
                </div>
            </aside>
            <style jsx>{`
                @keyframes drawerSlideIn {
                    from {
                        transform: translateX(24px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            `}</style>
        </div>
    );
}
