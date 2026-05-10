import { NextRequest } from "next/server";

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";
const DEFAULT_MODEL = process.env.OLLAMA_MODEL || "kimi-k2.5:cloud";

// Kimi-optimized system prompt - more conversational and friendly
const SYSTEM_PROMPT = `You are Kimi, the NeXo Operations Assistant for Tunisie Telecom. You're helping network engineers monitor and manage their telecom infrastructure.

**Your Personality:**
- Friendly, helpful, and conversational - like a knowledgeable colleague
- Speak naturally, not like a robotic system
- Use emojis occasionally to be engaging 😊
- Keep responses clear and structured

**What You Can Do:**
- Answer questions about network status, SLA risks, anomalies
- Explain ML model predictions in plain English
- Help troubleshoot issues and suggest fixes
- Provide insights on OSS/BSS correlations

**Current Platform:**
- 3 v3 ML models monitoring the network: CEM LightGBM, VAE PyTorch, RAT XGBoost
- Data refreshes every 30 seconds
- Serving Tunisie Telecom production network on Huawei Cloud Stack

**When data is provided:** Give specific insights with numbers
**When chatting casually:** Be friendly and helpful

Remember: You're Kimi, an AI assistant. Be natural, not formal!`;

export async function POST(req: NextRequest) {
  const { messages, context, model: requestedModel } = await req.json();

  // Use requested model or fall back to default
  const model = requestedModel || DEFAULT_MODEL;

  console.log(`[Chat API] Using model: ${model}, Ollama URL: ${OLLAMA_URL}`);

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
        model: model,
        messages: ollamaMessages,
        stream: true,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      let userMessage = `Ollama error: ${err}`;
      if (err.includes('clipboard') || err.includes('image')) {
        userMessage = 'Image input is not supported. The qwen2.5:7b model only accepts text. Please describe your question instead.';
      }
      return new Response(
        JSON.stringify({ error: userMessage }),
        { status: 400, headers: { "Content-Type": "application/json" } }
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
