import { NextResponse } from "next/server";
import { readFile, stat } from "fs/promises";
import path from "path";

// Resolve notebooks/models/metrics.json regardless of where the Next dev
// server was launched. Candidates checked in order. First hit wins.
//
//   1. METRICS_JSON_PATH env override (CI / Docker / explicit)
//   2. <cwd>/notebooks/models/metrics.json           (launched from project root)
//   3. <cwd>/../notebooks/models/metrics.json        (launched from dashboard/)
//   4. <__dirname>/../../../../notebooks/models/metrics.json (last-resort
//      relative to this route file when bundlers stash assets elsewhere)
//
// Returns 503 with the candidate list on miss so the page can render an
// honest remediation message instead of fabricating zeros.

export const dynamic = "force-dynamic";

function candidates(): string[] {
    const env = process.env.METRICS_JSON_PATH;
    const cwd = process.cwd();
    const list = [
        env,
        path.join(cwd, "notebooks", "models", "metrics.json"),
        path.resolve(cwd, "..", "notebooks", "models", "metrics.json"),
        path.resolve(__dirname, "..", "..", "..", "..", "notebooks", "models", "metrics.json"),
    ].filter((p): p is string => typeof p === "string" && p.length > 0);
    return Array.from(new Set(list));
}

async function findMetricsFile(): Promise<{ path: string; raw: string; mtime: Date } | null> {
    for (const candidate of candidates()) {
        try {
            const [raw, st] = await Promise.all([
                readFile(candidate, "utf-8"),
                stat(candidate),
            ]);
            return { path: candidate, raw, mtime: st.mtime };
        } catch {
            // try next
        }
    }
    return null;
}

export async function GET() {
    const hit = await findMetricsFile();
    if (!hit) {
        return NextResponse.json(
            {
                error: "no trained metrics found",
                detail: "notebooks/models/metrics.json missing — run scripts/dump_model_metrics.py or trigger pb-retrain-model",
                searched: candidates(),
                cwd: process.cwd(),
            },
            { status: 503 },
        );
    }
    try {
        const payload = JSON.parse(hit.raw);
        payload.fileMtime = hit.mtime.toISOString();
        payload.filePath = hit.path;
        return NextResponse.json(payload, {
            headers: { "Cache-Control": "no-store" },
        });
    } catch (err: any) {
        return NextResponse.json(
            { error: "invalid metrics.json", detail: String(err?.message ?? err), filePath: hit.path },
            { status: 500 },
        );
    }
}
