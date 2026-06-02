"use client";
import { type LucideIcon } from "lucide-react";

type Tone = "default" | "success" | "warning" | "danger" | "info";

interface Props {
    label: string;
    value: string | number;
    icon?: LucideIcon;
    tone?: Tone;
    sub?: string;
    delta?: { value: number; direction: "up" | "down" };
}

export default function StatTile({ label, value, icon: Icon, tone = "default", sub, delta }: Props) {
    return (
        <div className={`ui-stat-tile ui-stat-tile-${tone}`}>
            {Icon && (
                <div className="ui-stat-tile-icon">
                    <Icon size={16} strokeWidth={2.2} />
                </div>
            )}
            <div className="ui-stat-tile-body">
                <div className="ui-stat-tile-label">{label}</div>
                <div className="ui-stat-tile-value">{value}</div>
                {sub && <div className="ui-stat-tile-sub">{sub}</div>}
                {delta && (
                    <div className={`ui-stat-tile-delta ui-stat-tile-delta-${delta.direction}`}>
                        {delta.direction === "up" ? "▲" : "▼"} {Math.abs(delta.value)}%
                    </div>
                )}
            </div>
        </div>
    );
}
