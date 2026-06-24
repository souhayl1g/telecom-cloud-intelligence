import { NextResponse } from "next/server";
import { cookies } from "next/headers";

// Authoritative current-user (incl. role) for client components.
// Proxies auth-service /auth/me with the httpOnly cookie, so the role reflects
// the DB, not a possibly-stale client guess.
const authBase = process.env.AUTH_SERVICE_URL || "http://localhost:8002";

export async function GET() {
    const token = cookies().get("auth_token")?.value;
    if (!token) return NextResponse.json({ user: null }, { status: 200 });
    try {
        const r = await fetch(`${authBase}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
            cache: "no-store",
        });
        if (!r.ok) return NextResponse.json({ user: null }, { status: 200 });
        const user = await r.json();
        return NextResponse.json({ user }, { status: 200 });
    } catch {
        return NextResponse.json({ user: null }, { status: 200 });
    }
}
