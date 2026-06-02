"use client";
import { AlertOctagon, RotateCw } from "lucide-react";

interface Props {
    title?: string;
    message?: string;
    onRetry?: () => void;
    compact?: boolean;
}

export default function ErrorState({
    title = "Something went wrong",
    message = "We couldn't load this section. Try refreshing — the backend may be warming up.",
    onRetry,
    compact = false,
}: Props) {
    return (
        <div className={`ui-error-state ${compact ? "ui-error-state-compact" : ""}`} role="alert">
            <div className="ui-error-state-icon">
                <AlertOctagon size={compact ? 22 : 32} strokeWidth={1.8} />
            </div>
            <div>
                <div className="ui-error-state-title">{title}</div>
                {message && <div className="ui-error-state-message">{message}</div>}
            </div>
            {onRetry && (
                <button className="ui-error-state-btn" onClick={onRetry}>
                    <RotateCw size={14} strokeWidth={2.2} />
                    Retry
                </button>
            )}
        </div>
    );
}
