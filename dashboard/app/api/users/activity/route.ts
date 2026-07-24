import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

// User-activity feed proxy → auth-service (admin-guarded). Global feed by default;
// ?user_id=N returns that user's timeline (their own + actions taken on them).
const authBase = process.env.AUTH_SERVICE_URL || "http://localhost:8002";

export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const userId = req.nextUrl.searchParams.get("user_id");
    const limit = req.nextUrl.searchParams.get("limit") || "50";
    const url = userId
        ? `${authBase}/auth/users/${userId}/activity?limit=${limit}`
        : `${authBase}/auth/activity?limit=${limit}`;

    try {
        const r = await fetch(url, { headers, cache: "no-store" });
        const out = r.ok ? await r.json() : { error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: r.status });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
    }
}
