import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const qs = req.nextUrl.searchParams.toString();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
        const r = await fetch(`${base}/reports${qs ? `?${qs}` : ""}`, { headers, cache: "no-store" });
        const out = r.ok ? await r.json() : { reports: [], count: 0 };
        return NextResponse.json(out);
    } catch (e: any) {
        return NextResponse.json({ reports: [], count: 0, error: String(e?.message ?? e) }, { status: 200 });
    }
}

export async function POST(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const body = await req.json().catch(() => ({}));
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const r = await fetch(`${base}/reports/capacity`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        cache: "no-store",
    });
    const out = r.ok ? await r.json() : { error: "failed" };
    return NextResponse.json(out, { status: r.status });
}
