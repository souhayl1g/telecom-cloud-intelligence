import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const qs = req.nextUrl.searchParams.toString();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
        const [list, stats] = await Promise.all([
            fetch(`${base}/notifications${qs ? `?${qs}` : ""}`, { headers, cache: "no-store" }).then(r => r.ok ? r.json() : null),
            fetch(`${base}/notifications/stats`, { headers, cache: "no-store" }).then(r => r.ok ? r.json() : null),
        ]);
        return NextResponse.json({ notifications: list?.notifications ?? [], count: list?.count ?? 0, stats: stats ?? {} });
    } catch (e: any) {
        return NextResponse.json({ notifications: [], count: 0, stats: {}, error: String(e?.message ?? e) }, { status: 200 });
    }
}
