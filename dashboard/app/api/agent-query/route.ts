import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json(
    {
      error: "The agent-query endpoint has been deprecated.",
      message: "Please use /api/chat for all L4 Agent conversations.",
      migration_note: "The orchestrator mode has been merged into the unified chat. All queries now go through /api/chat with real reasoning pipeline and OpenRouter (free models) + Ollama fallback.",
    },
    { status: 410 }
  );
}
