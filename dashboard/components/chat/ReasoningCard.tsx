"use client";

import { useState } from "react";

export interface ReasoningStep {
  step: number;
  label: string;
  status: "running" | "done";
  detail?: string;
}

interface ReasoningCardProps {
  steps: ReasoningStep[];
  isComplete: boolean;
}

export default function ReasoningCard({ steps, isComplete }: ReasoningCardProps) {
  const [expanded, setExpanded] = useState(true);

  if (steps.length === 0) return null;

  const allDone = steps.every((s) => s.status === "done");

  return (
    <div className="l4-reasoning-card">
      <button
        className="l4-reasoning-header"
        onClick={() => setExpanded(!expanded)}
        type="button"
      >
        <span className="l4-reasoning-title">
          {allDone ? (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--brand-primary)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}>
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Analyzed
            </>
          ) : (
            <>
              <span className="l4-reasoning-pulse" />
              Thinking...
            </>
          )}
        </span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s",
            opacity: 0.6,
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {expanded && (
        <div className="l4-reasoning-steps">
          {steps.map((s) => (
            <div
              key={s.step}
              className={`l4-reasoning-step ${s.status === "done" ? "l4-reasoning-step-done" : "l4-reasoning-step-active"}`}
            >
              <span className="l4-reasoning-icon">
                {s.status === "done" ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--brand-primary)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <span className="l4-reasoning-dot" />
                )}
              </span>
              <span className="l4-reasoning-label">{s.label}</span>
              {s.detail && <span className="l4-reasoning-detail">{s.detail}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
