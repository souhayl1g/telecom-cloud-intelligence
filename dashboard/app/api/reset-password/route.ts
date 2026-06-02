import { NextRequest, NextResponse } from "next/server";

const AUTH_SERVICE = process.env.AUTH_SERVICE_URL || "http://auth-service:8002";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${AUTH_SERVICE}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json(
      { error: "Failed to process reset password request", detail: String(e) },
      { status: 500 }
    );
  }
}
