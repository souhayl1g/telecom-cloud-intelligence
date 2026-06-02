"use client";
/**
 * Animated loading skeleton primitives. Use instead of raw spinners on
 * data-fetching pages so layout doesn't jump when data arrives.
 */
interface SkeletonProps {
    width?: string | number;
    height?: string | number;
    radius?: number;
    className?: string;
}

export function Skeleton({ width = "100%", height = 16, radius = 6, className = "" }: SkeletonProps) {
    return (
        <span
            className={`ui-skeleton ${className}`}
            style={{ width, height, borderRadius: radius, display: "inline-block" }}
            aria-hidden="true"
        />
    );
}

export function SkeletonStatCard() {
    return (
        <div className="card card-compact">
            <Skeleton width={90} height={11} />
            <div style={{ height: 10 }} />
            <Skeleton width={120} height={28} radius={8} />
        </div>
    );
}

export function SkeletonChart({ height = 180 }: { height?: number }) {
    return (
        <div className="card card-accent-top">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <Skeleton width={10} height={10} radius={5} />
                <Skeleton width={160} height={14} />
            </div>
            <Skeleton width="100%" height={height} radius={10} />
        </div>
    );
}

export function SkeletonTable({ rows = 6 }: { rows?: number }) {
    return (
        <div className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <Skeleton width={10} height={10} radius={5} />
                <Skeleton width={140} height={14} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {Array.from({ length: rows }).map((_, i) => (
                    <div key={i} style={{ display: "flex", gap: 12 }}>
                        <Skeleton width={120} height={14} />
                        <Skeleton width={80} height={14} />
                        <Skeleton width={80} height={14} />
                        <Skeleton width={80} height={14} />
                        <Skeleton width={60} height={14} />
                    </div>
                ))}
            </div>
        </div>
    );
}

export function PageSkeleton({ withChart = true }: { withChart?: boolean }) {
    return (
        <div className="grid" style={{ gap: 20 }}>
            <div className="grid grid-4">
                <SkeletonStatCard />
                <SkeletonStatCard />
                <SkeletonStatCard />
                <SkeletonStatCard />
            </div>
            {withChart && (
                <div className="grid grid-2">
                    <SkeletonChart />
                    <SkeletonChart />
                </div>
            )}
            <SkeletonTable />
        </div>
    );
}
