"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function LiveIndicator() {
    const [secondsSinceUpdate, setSecondsSinceUpdate] = useState(0);
    const router = useRouter();

    useEffect(() => {
        const timer = setInterval(() => setSecondsSinceUpdate(prev => prev + 1), 1000);
        const refresher = setInterval(() => {
            router.refresh();
            setSecondsSinceUpdate(0);
        }, 120 * 1000);
        return () => { clearInterval(timer); clearInterval(refresher); };
    }, [router]);

    return (
        <div style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "var(--color-success-bg)",
            border: "1px solid var(--color-success-border)",
            padding: "3px 10px",
            borderRadius: "var(--radius-full)",
            fontSize: "10px",
            color: "var(--color-success)",
            fontWeight: 600,
            letterSpacing: "0.2px",
        }}>
            <div className="pulse-dot" style={{
                width: "6px",
                height: "6px",
                backgroundColor: "var(--color-success)",
                borderRadius: "50%",
                boxShadow: "0 0 6px var(--color-success)",
            }} />
            <span>LIVE</span>
            <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: '10px' }}>{secondsSinceUpdate}s</span>
        </div>
    );
}
