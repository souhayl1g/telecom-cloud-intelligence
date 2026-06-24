import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Notebook Lab proxy (Data Scientist/Admin). api-gateway enforces the role.
export async function GET() {
    const token = cookies().get("auth_token")?.value;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
        const r = await fetch(`${base}/notebooks/lab`, { headers, cache: "no-store" });
        const out = r.ok ? await r.json() : { cards: null, error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: 200 });
    } catch (e: any) {
        return NextResponse.json({ cards: null, error: String(e?.message ?? e) }, { status: 200 });
    }
}
