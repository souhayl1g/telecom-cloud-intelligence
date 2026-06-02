import { NextResponse } from "next/server";

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";

export async function GET() {
  try {
    const res = await fetch(`${OLLAMA_URL}/api/tags`, { cache: "no-store" });
    if (!res.ok) {
      return NextResponse.json(
        { error: "Ollama unreachable" },
        { status: 503 }
      );
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json(
      { error: "Cannot connect to Ollama", details: e?.message || String(e) },
      { status: 503 }
    );
  }
}
