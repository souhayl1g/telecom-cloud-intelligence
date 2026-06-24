import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Native Prometheus metrics proxy (Engineer/Admin). api-gateway enforces the role.
export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const qs = req.nextUrl.searchParams.toString();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
        const r = await fetch(`${base}/observability/metrics${qs ? `?${qs}` : ""}`, {
            headers, cache: "no-store",
        });
        const out = r.ok ? await r.json() : { panels: null, error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: 200 });
    } catch (e: any) {
        return NextResponse.json({ panels: null, error: String(e?.message ?? e) }, { status: 200 });
    }
}
