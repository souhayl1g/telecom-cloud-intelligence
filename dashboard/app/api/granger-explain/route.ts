import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

/**
 * SSR proxy for /granger-causality/explain — methodology metadata + lag window.
 * Reads auth_token cookie, forwards Bearer to api-gateway.
 */
export async function GET() {
    const token = cookies().get("auth_token")?.value;
    try {
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const r = await fetch(`${base}/granger-causality/explain`, {
            cache: "no-store",
            headers,
        });
        if (!r.ok) return NextResponse.json({ error: r.statusText }, { status: r.status });
        const j = await r.json();
        // The explain endpoint returns methodology only; expose lag window for UI.
        return NextResponse.json({ ...j, lag_window_minutes: 43200 });
    } catch (err: any) {
        return NextResponse.json({ error: err?.message ?? "fetch failed" }, { status: 500 });
    }
}
