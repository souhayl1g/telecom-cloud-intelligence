import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
    const area = req.nextUrl.searchParams.get("area");
    const token = cookies().get("auth_token")?.value;

    const url = area
        ? `${base}/granger-causality/lead-time?area=${encodeURIComponent(area)}`
        : `${base}/granger-causality/lead-time`;

    try {
        const res = await fetch(url, {
            cache: "no-store",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) {
            return NextResponse.json({ rows: [], lag_window_minutes: 0, error: `HTTP ${res.status}` });
        }
        return NextResponse.json(await res.json());
    } catch (e: any) {
        return NextResponse.json({ rows: [], lag_window_minutes: 0, error: e?.message || "fetch failed" });
    }
}
