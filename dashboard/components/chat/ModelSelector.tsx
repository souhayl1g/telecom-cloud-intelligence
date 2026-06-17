"use client";

import { useEffect, useState } from "react";

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  description: string;
  badge?: string;
}

interface ModelSelectorProps {
  value: string;
  onChange: (provider: string, model: string) => void;
  disabled?: boolean;
}

// OpenRouter (primary). Slugs verified live-free against GET /models. The chat route
// auto-falls-back across the free chain on 404/429, so any pick here degrades gracefully.
const STATIC_MODELS: ModelOption[] = [
  { id: "google/gemma-4-31b-it:free", name: "Gemma 4 31B", provider: "openrouter", description: "Reliable free default", badge: "free" },
  { id: "qwen/qwen3-next-80b-a3b-instruct:free", name: "Qwen3 Next 80B", provider: "openrouter", description: "Strong reasoning", badge: "free" },
  { id: "meta-llama/llama-3.3-70b-instruct:free", name: "Llama 3.3 70B", provider: "openrouter", description: "Capable Meta model", badge: "free" },
  { id: "nousresearch/hermes-3-llama-3.1-405b:free", name: "Hermes 3 405B", provider: "openrouter", description: "Largest free model", badge: "free" },
];

export default function ModelSelector({ value, onChange, disabled }: ModelSelectorProps) {
  const [ollamaModels, setOllamaModels] = useState<ModelOption[]>([]);
  const [ollamaError, setOllamaError] = useState(false);

  useEffect(() => {
    fetch("/api/ollama-tags", { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error("Ollama unreachable");
        return r.json();
      })
      .then((data) => {
        const models = (data.models || []).map((m: any) => ({
          id: m.name || m.model,
          name: m.name || m.model,
          provider: "ollama",
          description: `${m.details?.parameter_size || ""} ${m.details?.quantization_level || ""}`.trim() || "Local model",
          badge: "local",
        }));
        setOllamaModels(models);
        setOllamaError(false);
      })
      .catch(() => {
        setOllamaModels([]);
        setOllamaError(true);
      });
  }, []);

  const allModels = [...STATIC_MODELS, ...ollamaModels];
  const selected = allModels.find((m) => m.id === value) || allModels[0];

  const providers = [
    { key: "openrouter", label: "OpenRouter", description: "Primary — fast cloud inference" },
    { key: "ollama", label: "Local Ollama", description: ollamaError ? "Offline" : "Offline fallback" },
  ];

  return (
    <div className="l4-model-selector-bar">
      <select
        value={value}
        onChange={(e) => {
          const m = allModels.find((x) => x.id === e.target.value);
          if (m) onChange(m.provider, m.id);
        }}
        disabled={disabled}
        className="l4-model-select"
      >
        {providers.map((p) => {
          const groupModels = allModels.filter((m) => m.provider === p.key);
          if (groupModels.length === 0) return null;
          return (
            <optgroup key={p.key} label={`${p.label} — ${p.description}`}>
              {groupModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} {m.badge ? `[${m.badge}]` : ""}
                </option>
              ))}
            </optgroup>
          );
        })}
      </select>

      <button
        type="button"
        onClick={() => {
          if (confirm("Clear chat history?")) {
            localStorage.removeItem("l4-agent-chat-history");
            window.location.reload();
          }
        }}
        className="l4-clear-chat-btn"
        title="Clear chat"
        disabled={disabled}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
        <span>Clear</span>
      </button>
    </div>
  );
}
