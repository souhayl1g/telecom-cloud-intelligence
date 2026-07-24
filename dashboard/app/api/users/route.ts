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

// PATCH { user_id, ...fields } → full edit (email/full_name/role/is_active/password).
export async function PATCH(req: NextRequest) {
    const { user_id, ...fields } = await req.json().catch(() => ({} as any));
    if (!user_id) return NextResponse.json({ error: "user_id required" }, { status: 400 });
    try {
        const r = await fetch(`${authBase}/auth/users/${user_id}`, {
            method: "PATCH",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify(fields),
            cache: "no-store",
        });
        const out = await r.json().catch(() => ({}));
        return NextResponse.json(out, { status: r.status });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
    }
}

// DELETE ?id=N → remove a user.
export async function DELETE(req: NextRequest) {
    const id = req.nextUrl.searchParams.get("id");
    if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });
    try {
        const r = await fetch(`${authBase}/auth/users/${id}`, {
            method: "DELETE",
            headers: authHeaders(),
            cache: "no-store",
        });
        const out = await r.json().catch(() => ({}));
        return NextResponse.json(out, { status: r.status });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 500 });
    }
}
