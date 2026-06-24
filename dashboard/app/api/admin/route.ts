import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function authHeaders(extra: Record<string, string> = {}) {
    const token = cookies().get("auth_token")?.value;
    const h: Record<string, string> = { ...extra };
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
}

// Admin governance proxy (admin role enforced upstream).
//   GET  ?view=settings | pipeline   PATCH (settings)   POST ?action=reload-models
export async function GET(req: NextRequest) {
    const view = req.nextUrl.searchParams.get("view") || "settings";
    const path = view === "pipeline" ? "/admin/pipeline-status" : "/admin/settings";
    try {
        const r = await fetch(`${base}${path}`, { headers: authHeaders(), cache: "no-store" });
        const out = await r.json().catch(() => ({}));
        return NextResponse.json(out, { status: r.status });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
    }
}

export async function PATCH(req: NextRequest) {
    const body = await req.json().catch(() => ({}));
    try {
        const r = await fetch(`${base}/admin/settings`, {
            method: "PATCH",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify(body),
            cache: "no-store",
        });
        const out = await r.json().catch(() => ({}));
        return NextResponse.json(out, { status: r.status });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
    }
}

export async function POST(req: NextRequest) {
    const action = req.nextUrl.searchParams.get("action");
    if (action !== "reload-models") {
        return NextResponse.json({ error: "unknown action" }, { status: 400 });
    }
    try {
        const r = await fetch(`${base}/admin/pipeline/reload-models`, {
            method: "POST", headers: authHeaders(), cache: "no-store",
        });
        const out = await r.json().catch(() => ({}));
        return NextResponse.json(out, { status: r.status });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
    }
}
