import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(_req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
        const r = await fetch(`${base}/mlflow/summary`, { headers, cache: "no-store" });
        const out = r.ok
            ? await r.json()
            : { experiments: [], runs: [], registered_models: [], error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: 200 });
    } catch (e: any) {
        return NextResponse.json(
            { experiments: [], runs: [], registered_models: [], error: String(e?.message ?? e) },
            { status: 200 },
        );
    }
}
