"use client";
import { type LucideIcon } from "lucide-react";

interface Props {
    icon?: LucideIcon;
    title: string;
    subtitle?: string;
    action?: React.ReactNode;
    tone?: "default" | "danger" | "warning" | "success";
}

const TONE_DOT: Record<NonNullable<Props["tone"]>, string> = {
    default: "#007DBA",
    danger: "#DC2626",
    warning: "#F59E0B",
    success: "#10B981",
};

export default function SectionHeader({ icon: Icon, title, subtitle, action, tone = "default" }: Props) {
    return (
        <div className="ui-section-header">
            <div className="ui-section-header-left">
                <span className="ui-section-header-dot" style={{ background: TONE_DOT[tone] }} />
                {Icon && (
                    <span className="ui-section-header-icon" style={{ color: TONE_DOT[tone] }}>
                        <Icon size={15} strokeWidth={2.2} />
                    </span>
                )}
                <h3 className="ui-section-header-title">{title}</h3>
                {subtitle && <span className="ui-section-header-sub">{subtitle}</span>}
            </div>
            {action && <div className="ui-section-header-action">{action}</div>}
        </div>
    );
}
