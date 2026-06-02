"use client";
import { Inbox, type LucideIcon } from "lucide-react";

interface Props {
    title?: string;
    description?: string;
    icon?: LucideIcon;
    action?: { label: string; onClick: () => void };
    compact?: boolean;
}

export default function EmptyState({
    title = "No data yet",
    description = "Data will appear here once the pipeline produces results.",
    icon: Icon = Inbox,
    action,
    compact = false,
}: Props) {
    return (
        <div className={`ui-empty-state ${compact ? "ui-empty-state-compact" : ""}`}>
            <div className="ui-empty-state-icon">
                <Icon size={compact ? 22 : 32} strokeWidth={1.6} />
            </div>
            <div className="ui-empty-state-title">{title}</div>
            {description && <div className="ui-empty-state-desc">{description}</div>}
            {action && (
                <button className="ui-empty-state-btn" onClick={action.onClick}>
                    {action.label}
                </button>
            )}
        </div>
    );
}
