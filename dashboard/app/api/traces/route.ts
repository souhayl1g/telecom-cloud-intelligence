import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Native Jaeger trace proxy (Engineer/Admin).
//   ?list=services  -> service dropdown
//   ?service=X      -> recent traces for that service
export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const sp = req.nextUrl.searchParams;
    const upstream = sp.get("list") === "services"
        ? "/observability/services"
        : `/observability/traces?${sp.toString()}`;
    try {
        const r = await fetch(`${base}${upstream}`, { headers, cache: "no-store" });
        const out = r.ok ? await r.json() : { traces: null, services: null, error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: 200 });
    } catch (e: any) {
        return NextResponse.json({ traces: null, services: null, error: String(e?.message ?? e) }, { status: 200 });
    }
}
