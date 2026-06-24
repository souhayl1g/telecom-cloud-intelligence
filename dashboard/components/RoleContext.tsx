"use client";
import { createContext, useContext, useEffect, useState } from "react";
import type { Role } from "../lib/roles";

interface CurrentUser {
    id: number;
    email: string;
    full_name: string | null;
    role: Role;
}

interface RoleContextValue {
    user: CurrentUser | null;
    role: Role | undefined;
    loading: boolean;
}

const RoleContext = createContext<RoleContextValue>({
    user: null,
    role: undefined,
    loading: true,
});

// Fetches the authoritative current user once (role included) and shares it.
// One fetch for the whole app instead of every component re-asking.
export function RoleProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<CurrentUser | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let alive = true;
        fetch("/api/me", { cache: "no-store" })
            .then((r) => r.json())
            .then((d) => { if (alive) setUser(d.user ?? null); })
            .catch(() => { if (alive) setUser(null); })
            .finally(() => { if (alive) setLoading(false); });
        return () => { alive = false; };
    }, []);

    return (
        <RoleContext.Provider value={{ user, role: user?.role, loading }}>
            {children}
        </RoleContext.Provider>
    );
}

export const useRole = () => useContext(RoleContext);
