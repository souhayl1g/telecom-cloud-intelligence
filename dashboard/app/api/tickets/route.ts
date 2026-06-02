import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const sp = req.nextUrl.searchParams;
    const qs = sp.toString();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
        const [list, stats] = await Promise.all([
            fetch(`${base}/tickets${qs ? `?${qs}` : ""}`, { headers, cache: "no-store" }).then(r => r.ok ? r.json() : null),
            fetch(`${base}/tickets/stats`, { headers, cache: "no-store" }).then(r => r.ok ? r.json() : null),
        ]);
        return NextResponse.json({ tickets: list?.tickets ?? [], count: list?.count ?? 0, stats: stats ?? {} });
    } catch (e: any) {
        return NextResponse.json({ tickets: [], count: 0, stats: {}, error: String(e?.message ?? e) }, { status: 200 });
    }
}

export async function POST(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const body = await req.json();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const r = await fetch(`${base}/tickets`, { method: "POST", headers, body: JSON.stringify(body), cache: "no-store" });
    const out = r.ok ? await r.json() : { error: "failed" };
    return NextResponse.json(out, { status: r.status });
}
