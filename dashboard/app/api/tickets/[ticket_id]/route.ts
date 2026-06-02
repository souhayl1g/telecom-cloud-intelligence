import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function PATCH(req: NextRequest, { params }: { params: { ticket_id: string } }) {
    const token = cookies().get("auth_token")?.value;
    const body = await req.json();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const r = await fetch(`${base}/tickets/${params.ticket_id}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify(body),
        cache: "no-store",
    });
    const out = r.ok ? await r.json() : { error: "failed" };
    return NextResponse.json(out, { status: r.status });
}
