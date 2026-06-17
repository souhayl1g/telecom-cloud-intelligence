import { NextRequest } from "next/server";
import { query } from "../../../lib/db";

// ── Provider configs ───────────────────────────────────────────────
// OpenRouter is the only cloud provider (free models only). Ollama is the
// local fallback when no API key is configured.
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || "";
// NOTE: OpenRouter rotates which models stay on the free tier. `deepseek-chat-v3-0324:free`
// was delisted (404: "use deepseek/deepseek-chat-v3-0324" — paid). Defaults/fallbacks below
// were verified live-free against GET /models. Free models also flap to HTTP 429 minute to
// minute, so a single slug is never enough — see the fallback loop in POST().
const OPENROUTER_DEFAULT_MODEL = process.env.OPENROUTER_DEFAULT_MODEL || "google/gemma-4-31b-it:free";
// Ordered free-model fallback chain. On 404 (delisted) or 429 (rate-limited) we advance to the
// next slug *before the first token is streamed*. Override the head via OPENROUTER_DEFAULT_MODEL.
const OPENROUTER_FREE_FALLBACKS = [
  "google/gemma-4-31b-it:free",
  "qwen/qwen3-next-80b-a3b-instruct:free",
  "meta-llama/llama-3.3-70b-instruct:free",
  "nousresearch/hermes-3-llama-3.1-405b:free",
  "google/gemma-4-26b-a4b-it:free",
];
const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";
const OLLAMA_DEFAULT_MODEL = process.env.OLLAMA_DEFAULT_MODEL || "qwen2.5:7b";

// ── System prompt (v3.0 reality) ───────────────────────────────────
const SYSTEM_PROMPT = `You are NeXo, the AI Operations Assistant for Tunisie Telecom's CEM-CVM Intelligence Platform.
You help network operators analyze CEM scores, VAE anomalies, RAT underservice, and Granger causality.

Instructions:
- Be concise, technical, and actionable.
- Always cite specific numbers from the context.
- If asked about anomalies, reference the VAE anomaly count and affected areas.
- If asked about subscriber experience, reference CEM scores and poor-count.
- If asked about capacity, reference RAT underservice rate and headroom.
- If data is missing, say so honestly — never invent numbers.
- Use markdown formatting: bullet points, bold for key numbers, code blocks for technical details.`;

// ── Prompt-injection guard ─────────────────────────────────────────
const INJECTION_PATTERNS = [
  /ignore\s+previous/i, /ignore\s+above/i, /ignore\s+all/i,
  /system\s+prompt/i, /you\s+are\s+now/i, /new\s+instruction/i,
  /override\s+instructions?/i, /disregard\s+everything/i,
  /forget\s+everything/i, /DAN\s+mode/i, /jailbreak/i,
  /ignore\s+your\s+reasoning/i, /skip\s+reasoning/i,
];

function sanitizeContext(ctx: unknown): Record<string, unknown> {
  if (!ctx || typeof ctx !== "object") return {};
  const allowedKeys = [
    "cemScores", "vaeAnomalies", "ratUnderservice",
    "grangerCausality", "pipelineRuns", "agentActions",
    "correlations", "kpiSummary",
  ];
  const safe: Record<string, unknown> = {};
  for (const key of allowedKeys) {
    if (key in ctx) safe[key] = (ctx as Record<string, unknown>)[key];
  }
  return safe;
}

function scrubText(text: string): string {
  for (const p of INJECTION_PATTERNS) text = text.replace(p, "[REDACTED]");
  return text;
}

// ── Intent classification (local, real) ────────────────────────────
type Intent = "cem_scores" | "vae_anomalies" | "rat_underservice" | "granger" | "pipeline" | "actions" | "general";

function classifyIntent(userMessage: string): Intent[] {
  const msg = userMessage.toLowerCase();
  const needs: Intent[] = [];
  if (/\b(cem|score|subscriber|experience|customer|quality)\b/.test(msg)) needs.push("cem_scores");
  if (/\b(anomal|vae|outlier|fault|issue|problem|detect)\b/.test(msg)) needs.push("vae_anomalies");
  if (/\b(rat|underservice|capacity|bandwidth|throughput|load|cell|tower)\b/.test(msg)) needs.push("rat_underservice");
  if (/\b(granger|correlation|causality|oss|oss-cem|convergence)\b/.test(msg)) needs.push("granger");
  if (/\b(pipeline|run|cycle|ingest|etl|job)\b/.test(msg)) needs.push("pipeline");
  if (/\b(action|approve|reject|ticket|playbook|intervention|alert)\b/.test(msg)) needs.push("actions");
  if (needs.length === 0) needs.push("general");
  return needs;
}

function intentLabel(intent: Intent): string {
  const map: Record<Intent, string> = {
    cem_scores: "CEM subscriber scores",
    vae_anomalies: "VAE anomaly detection",
    rat_underservice: "RAT underservice & capacity",
    granger: "OSS↔CEM Granger causality",
    pipeline: "Pipeline execution status",
    actions: "Agent actions & playbooks",
    general: "platform overview",
  };
  return map[intent];
}

// ── Live data fetching (real DB queries) ───────────────────────────
interface LiveContext {
  cemScores?: Record<string, unknown>;
  vaeAnomalies?: Record<string, unknown>;
  ratUnderservice?: Record<string, unknown>;
  grangerCausality?: Record<string, unknown>;
  pipelineRuns?: Record<string, unknown>;
  agentActions?: Record<string, unknown>;
}

async function fetchLiveData(intents: Intent[], clientContext: Record<string, unknown>): Promise<LiveContext> {
  const result: LiveContext = {};

  for (const intent of intents) {
    if (intent === "cem_scores") {
      const clientCem = clientContext.cemScores as Record<string, unknown> | undefined;
      if (clientCem && clientCem.cemAvgScore !== undefined) {
        result.cemScores = clientCem;
      } else {
        const [row] = await query<{ avg: number; total: number; poor: number }>(
          `SELECT COALESCE(AVG(cem_score),0)::float8 AS avg,
                  COUNT(*)::int AS total,
                  COUNT(*) FILTER (WHERE cem_score < 0.3)::int AS poor
             FROM subscriber_features WHERE cem_score IS NOT NULL`
        );
        result.cemScores = {
          cemAvgScore: row?.avg ? Number(row.avg.toFixed(3)) : null,
          cemTotalSubscribers: row?.total ?? 0,
          cemPoorCount: row?.poor ?? 0,
        };
      }
    }

    if (intent === "vae_anomalies") {
      const clientVae = clientContext.vaeAnomalies as Record<string, unknown> | undefined;
      if (clientVae && clientVae.vaeAnomalyCount !== undefined) {
        result.vaeAnomalies = clientVae;
      } else {
        const [row] = await query<{ total: number; anom: number; areas: number }>(
          `SELECT COUNT(*)::int AS total,
                  COUNT(*) FILTER (WHERE is_anomaly = TRUE)::int AS anom,
                  COUNT(DISTINCT region) FILTER (WHERE is_anomaly = TRUE)::int AS areas
             FROM vae_anomaly_scores`
        );
        const total = row?.total ?? 1;
        result.vaeAnomalies = {
          vaeAnomalyCount: row?.anom ?? 0,
          vaeAnomalyRate: total ? Number(((row?.anom ?? 0) / total * 100).toFixed(2)) : 0,
          vaeAreasAffected: row?.areas ?? 0,
        };
      }
    }

    if (intent === "rat_underservice") {
      const clientRat = clientContext.ratUnderservice as Record<string, unknown> | undefined;
      if (clientRat && clientRat.ratUnderserved !== undefined) {
        result.ratUnderservice = clientRat;
      } else {
        const [row] = await query<{ under: number; total: number }>(
          `SELECT COUNT(*) FILTER (WHERE rat_gap_score > 0.3)::int AS under,
                  COUNT(*)::int AS total
             FROM subscriber_features WHERE rat_gap_score IS NOT NULL`
        );
        const total = row?.total ?? 1;
        result.ratUnderservice = {
          ratUnderserved: row?.under ?? 0,
          ratUnderserviceRate: total ? Number(((row?.under ?? 0) / total * 100).toFixed(2)) : 0,
        };
      }
    }

    if (intent === "granger") {
      const clientGranger = clientContext.grangerCausality as Record<string, unknown> | undefined;
      if (clientGranger && clientGranger.grangerSignificantPairs !== undefined) {
        result.grangerCausality = clientGranger;
      } else {
        const [row] = await query<{ sig: number; total: number }>(
          `SELECT COUNT(*) FILTER (WHERE significant)::int AS sig,
                  COUNT(*)::int AS total
             FROM granger_causality_results`
        );
        result.grangerCausality = {
          grangerSignificantPairs: row?.sig ?? 0,
          correlationsCount: row?.total ?? 0,
        };
      }
    }

    if (intent === "pipeline") {
      const clientPipe = clientContext.pipelineRuns as Record<string, unknown> | undefined;
      if (clientPipe && clientPipe.pipelineRuns !== undefined) {
        result.pipelineRuns = clientPipe;
      } else {
        const [row] = await query<{ runs: number; last_status: string }>(
          `SELECT COUNT(*)::int AS runs,
                  COALESCE((SELECT status FROM pipeline_runs ORDER BY started_at DESC LIMIT 1), 'unknown') AS last_status
             FROM pipeline_runs`
        );
        result.pipelineRuns = {
          pipelineRuns: row?.runs ?? 0,
          lastPipelineStatus: row?.last_status ?? "unknown",
        };
      }
    }

    if (intent === "actions") {
      const clientActions = clientContext.agentActions as Record<string, unknown> | undefined;
      if (clientActions && clientActions.pendingActions !== undefined) {
        result.agentActions = clientActions;
      } else {
        const [row] = await query<{ pending: number; auto: number }>(
          `SELECT COUNT(*) FILTER (WHERE status = 'pending')::int AS pending,
                  COUNT(*) FILTER (WHERE status = 'auto_approved')::int AS auto
             FROM agent_actions`
        );
        result.agentActions = {
          pendingActions: row?.pending ?? 0,
          autoApprovedCount: row?.auto ?? 0,
        };
      }
    }

    if (intent === "general") {
      // Fetch everything
      const allIntents: Intent[] = ["cem_scores", "vae_anomalies", "rat_underservice", "granger", "pipeline", "actions"];
      for (const sub of allIntents) {
        if (!result[sub.replace(/_([a-z])/g, (_, c) => c.toUpperCase()) as keyof LiveContext]) {
          const subData = await fetchLiveData([sub], clientContext);
          Object.assign(result, subData);
        }
      }
    }
  }

  return result;
}

// ── Provider streaming helpers ─────────────────────────────────────

async function* streamOpenAICompatible(
  baseUrl: string,
  apiKey: string,
  model: string,
  messages: Array<{ role: string; content: string }>,
  extraHeaders?: Record<string, string>
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${apiKey}`,
    ...extraHeaders,
  };

  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model,
      messages,
      stream: true,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("Response has no body");

  const decoder = new TextDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n").filter(Boolean);
      for (const line of lines) {
        if (line.trim() === "data: [DONE]") continue;
        if (line.startsWith("data: ")) {
          try {
            const json = JSON.parse(line.slice(6));
            const text = json.choices?.[0]?.delta?.content || "";
            if (text) yield text;
          } catch {
            // skip
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ── Main handler ───────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const {
    messages,
    context: clientContext = {},
    provider: requestedProvider,
    model: requestedModel,
  } = body;

  if (!Array.isArray(messages) || messages.length === 0) {
    return new Response(JSON.stringify({ error: "Missing messages" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Only OpenRouter (free cloud models) and Ollama (local fallback) are supported.
  const allowedProviders = ["openrouter", "ollama"];
  let provider = allowedProviders.includes(requestedProvider as string) ? (requestedProvider as string) : "";

  const hasOpenRouter = OPENROUTER_API_KEY.startsWith("sk-or-") && OPENROUTER_API_KEY.length > 10;

  if (!provider) {
    if (hasOpenRouter) provider = "openrouter";
    else provider = "ollama";
  }

  // Fallback chain
  const originalProvider = provider;
  let fallbackReason = "";
  if (provider === "openrouter" && !hasOpenRouter) {
    fallbackReason = "OpenRouter API key missing";
    provider = "ollama";
  }
  if (provider === "ollama" && originalProvider !== "ollama" && !fallbackReason) {
    fallbackReason = "Falling back to local Ollama";
  }

  // ALWAYS pick the correct model for the final provider (critical for fallback)
  const model =
    provider === "openrouter" ? (requestedModel || OPENROUTER_DEFAULT_MODEL)
    : OLLAMA_DEFAULT_MODEL;

  const userMessage = messages[messages.length - 1]?.content || "";
  const safeUserMessage = scrubText(userMessage);

  // ── Start SSE stream ──
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const send = (event: string, data: unknown) => {
        controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
      };

      try {
        // Step 1: Understanding question
        send("reasoning", { step: 1, label: "Understanding question...", status: "running" });
        const intents = classifyIntent(safeUserMessage);
        send("reasoning", { step: 1, label: "Understanding question...", status: "done", detail: intents.map(intentLabel).join(", ") });

        // Step 2: Gathering live data
        send("reasoning", { step: 2, label: `Gathering live data (${intents.map(intentLabel).join(", ")})...`, status: "running" });
        const liveData = await fetchLiveData(intents, sanitizeContext(clientContext));
        send("reasoning", { step: 2, label: "Gathering live data...", status: "done" });

        // Step 3: Analyzing platform state
        send("reasoning", { step: 3, label: "Analyzing platform state...", status: "running" });
        // Light analysis: build a summary sentence for the context
        const analysisParts: string[] = [];
        if (liveData.cemScores) {
          const c = liveData.cemScores;
          analysisParts.push(`CEM avg ${c.cemAvgScore ?? "—"} over ${c.cemTotalSubscribers ?? 0} subscribers (${c.cemPoorCount ?? 0} poor).`);
        }
        if (liveData.vaeAnomalies) {
          const v = liveData.vaeAnomalies;
          analysisParts.push(`${v.vaeAnomalyCount ?? 0} VAE anomalies across ${v.vaeAreasAffected ?? 0} areas.`);
        }
        if (liveData.ratUnderservice) {
          const r = liveData.ratUnderservice;
          analysisParts.push(`${r.ratUnderserved ?? 0} RAT-underserved subscribers (${r.ratUnderserviceRate ?? 0}%).`);
        }
        if (liveData.grangerCausality) {
          const g = liveData.grangerCausality;
          analysisParts.push(`${g.grangerSignificantPairs ?? 0} significant Granger pairs.`);
        }
        send("reasoning", { step: 3, label: "Analyzing platform state...", status: "done", detail: analysisParts.join(" ") });

        // Build filtered context string
        const filteredContext = JSON.stringify(liveData, null, 2);
        const systemContent = `${SYSTEM_PROMPT}\n\n--- LIVE PLATFORM DATA ---\n${filteredContext}\n\n--- ANALYSIS ---\n${analysisParts.join(" ")}`;

        const llmMessages = [
          { role: "system", content: systemContent },
          ...messages.map((m: { role: string; content: string }) => ({
            role: m.role,
            content: scrubText(m.content),
          })),
        ];

        // Step 4: Formulating response
        const providerLabel = provider === originalProvider ? provider : `${provider} (fallback: ${fallbackReason || 'preferred provider unavailable'})`;
        send("reasoning", { step: 4, label: `Formulating response via ${providerLabel}...`, status: "running" });

        let streamError: string | null = null;

        try {
          if (provider === "openrouter") {
            const extraHeaders: Record<string, string> = {
              "HTTP-Referer": process.env.VERCEL_URL || "http://localhost:3001",
              "X-Title": "NeXo L4 Agent",
            };
            // Try the requested model first, then walk the free-model fallback chain.
            // We can only switch models BEFORE the first token is sent — once we start
            // streaming, a mid-stream error must surface (can't restart the response).
            const candidates = [model, ...OPENROUTER_FREE_FALLBACKS.filter((m) => m !== model)];
            let sentAny = false;
            let lastErr: string | null = null;
            for (let i = 0; i < candidates.length; i++) {
              const cand = candidates[i];
              try {
                for await (const chunk of streamOpenAICompatible(OPENROUTER_BASE_URL, OPENROUTER_API_KEY, cand, llmMessages, extraHeaders)) {
                  sentAny = true;
                  send("message", { content: chunk });
                }
                lastErr = null;
                break; // streamed cleanly
              } catch (err: any) {
                lastErr = err?.message || String(err);
                // If we already streamed text, we cannot fall back — re-raise.
                if (sentAny) throw err;
                // Otherwise advance to the next free model (covers 404 delisted / 429 rate-limited).
                if (i < candidates.length - 1) {
                  send("reasoning", { step: 4, label: `Model ${cand} unavailable — retrying with ${candidates[i + 1]}...`, status: "running" });
                }
              }
            }
            if (!sentAny && lastErr) {
              throw new Error(`all free models exhausted (last: ${lastErr})`);
            }
          } else {
            // Ollama native endpoint is /api/chat, not /v1/chat/completions
            const ollamaMessages = llmMessages.map((m) => ({
              role: m.role,
              content: m.content,
            }));
            const res = await fetch(`${OLLAMA_URL}/api/chat`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ model, messages: ollamaMessages, stream: true }),
            });
            if (!res.ok) {
              const errText = await res.text().catch(() => "");
              if (res.status === 404) {
                throw new Error(`Ollama model '${model}' not found. Run: ollama pull ${model}`);
              }
              throw new Error(`Ollama error ${res.status}: ${errText.slice(0, 200)}`);
            }
            const reader = res.body?.getReader();
            if (!reader) throw new Error("Ollama response has no body");
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
                      send("message", { content: json.message.content });
                    }
                  } catch {
                    // skip
                  }
                }
              }
            } finally {
              reader.releaseLock();
            }
          }
        } catch (e: any) {
          streamError = e?.message || String(e);
          let userHint = "";
          if (provider === "ollama" && originalProvider !== "ollama") {
            userHint = "\n\n[OpenRouter unavailable — using local Ollama fallback. Add OPENROUTER_API_KEY to dashboard/.env.local for cloud inference.]";
          }
          if (streamError && streamError.includes("not found")) {
            userHint += `\n\n[${streamError}]`;
          }
          send("message", { content: `\n\n*[${provider} failed: ${streamError}]*${userHint}` });
        }

        send("reasoning", { step: 4, label: "Formulating response...", status: "done" });
        send("done", { provider, model, error: streamError });
      } catch (e: any) {
        send("error", { message: e?.message || String(e) });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
