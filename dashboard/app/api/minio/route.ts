import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Native MinIO browser proxy (Data Scientist/Admin).
//   (no params)                  -> buckets + counts
//   ?bucket=X[&prefix=]          -> objects in bucket
//   ?bucket=X&key=Y&presign=1    -> presigned download URL
export async function GET(req: NextRequest) {
    const token = cookies().get("auth_token")?.value;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const sp = req.nextUrl.searchParams;

    let upstream = "/storage/buckets";
    if (sp.get("presign") === "1" && sp.get("bucket") && sp.get("key")) {
        upstream = `/storage/presign?bucket=${encodeURIComponent(sp.get("bucket")!)}&key=${encodeURIComponent(sp.get("key")!)}`;
    } else if (sp.get("bucket")) {
        const qs = new URLSearchParams({ bucket: sp.get("bucket")!, prefix: sp.get("prefix") || "" });
        upstream = `/storage/objects?${qs.toString()}`;
    }

    try {
        const r = await fetch(`${base}${upstream}`, { headers, cache: "no-store" });
        const out = r.ok ? await r.json() : { error: `upstream ${r.status}` };
        return NextResponse.json(out, { status: 200 });
    } catch (e: any) {
        return NextResponse.json({ error: String(e?.message ?? e) }, { status: 200 });
    }
}
