import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Data Explorer proxy (Data Scientist/Admin).
export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const qs = req.nextUrl.searchParams.toString();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
        const r = await fetch(`${base}/explorer/summary${qs ? `?${qs}` : ""}`, { headers, cache: "no-store" });
        const out = r.ok ? await r.json() : { features: null, error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: 200 });
    } catch (e: any) {
        return NextResponse.json({ features: null, error: String(e?.message ?? e) }, { status: 200 });
    }
}
