import { NextRequest } from "next/server";

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";
const MODEL = process.env.OLLAMA_MODEL || "qwen2.5:7b";

const SYSTEM_PROMPT = `You are the NexOps L4 Autonomous Agent — an AI Operations intelligence engine embedded in the Telecom Cloud Intelligence Platform built for Huawei's ADN (Autonomous Driving Network) architecture.

Your role:
- You are the L4 (Autonomous) level agent in the TM Forum Autonomous Network framework
- You analyze OSS (Network) and BSS (Business) telemetry data in real-time
- You provide actionable intelligence for Tunisie Telecom network operations
- You can recommend auto-remediations, predict SLA breaches, detect anomalies, and correlate OSS-BSS signals

Platform context:
- 3 ML models: GradientBoostingRegressor (SLA risk), IsolationForest (OSS anomaly), IsolationForest (BSS revenue anomaly)
- Pipeline runs every 120 seconds with sliding window data ingestion
- Data flows: CEM/SmartCare -> Pipeline Worker -> MinIO Data Lake -> AI Service -> PostgreSQL -> Dashboard
- KPIs: throughput_mbps, latency_ms, packet_loss_pct, active_users, signal_rsrp_dbm (OSS) and revenue_tnd, data_used_gb, voice_min, sms_count, churn_risk (BSS)

When the user provides live platform data in the context, analyze it thoroughly and provide:
1. Risk assessment with specific numbers
2. Root cause analysis when anomalies are detected
3. Concrete remediation actions (not generic advice)
4. Predictions for the next monitoring window

Be concise, technical, and action-oriented. Use telecom terminology. Format responses with clear sections. You speak as the L4 Agent, not as a generic AI assistant.`;

export async function POST(req: NextRequest) {
  const { messages, context } = await req.json();

  // Build the full message list with system prompt + optional live context
  const systemContent = context
    ? `${SYSTEM_PROMPT}\n\n--- LIVE PLATFORM DATA ---\n${JSON.stringify(context, null, 2)}`
    : SYSTEM_PROMPT;

  const ollamaMessages = [
    { role: "system", content: systemContent },
    ...messages,
  ];

  try {
    const response = await fetch(`${OLLAMA_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: MODEL,
        messages: ollamaMessages,
        stream: true,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      return new Response(
        JSON.stringify({ error: `Ollama error: ${err}` }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }

    // Stream the response back
    const encoder = new TextEncoder();
    const readable = new ReadableStream({
      async start(controller) {
        const reader = response.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }

        const decoder = new TextDecoder();
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n").filter(Boolean);

            for (const line of lines) {
              try {
                const json = JSON.parse(line);
                if (json.message?.content) {
                  controller.enqueue(
                    encoder.encode(`data: ${JSON.stringify({ content: json.message.content })}\n\n`)
                  );
                }
                if (json.done) {
                  controller.enqueue(encoder.encode("data: [DONE]\n\n"));
                }
              } catch {
                // skip malformed lines
              }
            }
          }
        } catch (e) {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ error: String(e) })}\n\n`)
          );
        } finally {
          controller.close();
        }
      },
    });

    return new Response(readable, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (e) {
    return new Response(
      JSON.stringify({
        error: "Cannot connect to Ollama. Ensure it is running on localhost:11434",
        details: String(e),
      }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}
