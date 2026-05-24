import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

/**
 * SSR proxy for /granger-causality/forecast. Reads auth_token cookie and
 * forwards Bearer to api-gateway. Supports ?area=X passthrough.
 */
export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const area = req.nextUrl.searchParams.get("area");
    try {
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const url = `${base}/granger-causality/forecast${area ? `?area=${encodeURIComponent(area)}` : ""}`;
        const r = await fetch(url, { cache: "no-store", headers });
        if (!r.ok) return NextResponse.json({ error: r.statusText }, { status: r.status });
        return NextResponse.json(await r.json());
    } catch (err: any) {
        return NextResponse.json({ error: err?.message ?? "fetch failed" }, { status: 500 });
    }
}
