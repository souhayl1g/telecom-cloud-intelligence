import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

// Admin user/role management proxy → auth-service. The httpOnly token is
// forwarded; auth-service enforces the admin role (403 otherwise).
const authBase = process.env.AUTH_SERVICE_URL || "http://localhost:8002";

function authHeaders(extra: Record<string, string> = {}) {
    const token = cookies().get("auth_token")?.value;
    const h: Record<string, string> = { ...extra };
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
}

export async function GET() {
    try {
        const r = await fetch(`${authBase}/auth/users`, { headers: authHeaders(), cache: "no-store" });
        const out = r.ok ? await r.json() : { error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: r.status });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
    }
}

export async function POST(req: NextRequest) {
    const body = await req.json().catch(() => ({}));
    try {
        const r = await fetch(`${authBase}/auth/users`, {
            method: "POST",
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

// PATCH { user_id, role } or { user_id, is_active } → route to the right sub-endpoint.
export async function PATCH(req: NextRequest) {
    const { user_id, role, is_active } = await req.json().catch(() => ({} as any));
    if (!user_id) return NextResponse.json({ error: "user_id required" }, { status: 400 });
    const sub = role !== undefined
        ? { path: `role`, body: { role } }
        : { path: `active`, body: { is_active } };
    try {
        const r = await fetch(`${authBase}/auth/users/${user_id}/${sub.path}`, {
            method: "PATCH",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify(sub.body),
            cache: "no-store",
        });
        const out = await r.json().catch(() => ({}));
        return NextResponse.json(out, { status: r.status });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
    }
}
