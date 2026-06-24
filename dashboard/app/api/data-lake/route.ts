import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// SSR proxy for the Converged Data Lake summary. The data-lake page is a client
// component and cannot read the httpOnly auth_token cookie, so the token is read
// here and forwarded as a Bearer header (same pattern as /api/platform-data).
export async function GET(_req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
        const r = await fetch(`${base}/data-lake/summary`, { headers, cache: "no-store" });
        // Honesty: on failure return null fields, never fabricated zeros.
        const out = r.ok
            ? await r.json()
            : { sources: null, layers: null, twin: null, error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: 200 });
    } catch (e: any) {
        return NextResponse.json(
            { sources: null, layers: null, twin: null, error: String(e?.message ?? e) },
            { status: 200 },
        );
    }
}
