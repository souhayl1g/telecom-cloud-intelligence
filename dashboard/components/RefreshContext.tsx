"use client";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';

interface RefreshContextValue {
    tick: number;
    lastRefreshed: Date | null;
    refreshNow: () => void;
    paused: boolean;
    setPaused: (v: boolean) => void;
    intervalMs: number;
}

const RefreshContext = createContext<RefreshContextValue>({
    tick: 0,
    lastRefreshed: null,
    refreshNow: () => {},
    paused: false,
    setPaused: () => {},
    intervalMs: 120000,
});

export function RefreshProvider({ children, intervalMs = 120000 }: { children: React.ReactNode; intervalMs?: number }) {
    const [tick, setTick] = useState(0);
    const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
    const [paused, setPaused] = useState(false);
    const pausedRef = useRef(paused);
    pausedRef.current = paused;

    useEffect(() => {
        const id = setInterval(() => {
            if (pausedRef.current) return;
            if (document.visibilityState === 'hidden') return;
            setTick((t) => t + 1);
            setLastRefreshed(new Date());
        }, intervalMs);
        return () => clearInterval(id);
    }, [intervalMs]);

    const value = useMemo<RefreshContextValue>(() => ({
        tick,
        lastRefreshed,
        refreshNow: () => {
            setTick((t) => t + 1);
            setLastRefreshed(new Date());
        },
        paused,
        setPaused,
        intervalMs,
    }), [tick, lastRefreshed, paused, intervalMs]);

    return <RefreshContext.Provider value={value}>{children}</RefreshContext.Provider>;
}

export function useRefresh() {
    return useContext(RefreshContext);
}
