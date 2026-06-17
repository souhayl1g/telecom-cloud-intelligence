"use client";

interface StarterQuestionsProps {
  onSelect: (question: string) => void;
  vaeAnomalyCount?: number;
  cemPoorCount?: number;
}

export default function StarterQuestions({ onSelect, vaeAnomalyCount, cemPoorCount }: StarterQuestionsProps) {
  const questions = [
    "Analyze current CEM scores and identify poor-experience areas",
    "What VAE anomalies were detected in the latest pipeline run?",
    "Summarize OSS to CEM Granger causality insights",
  ];

  const displayQuestions = [...questions];
  if (vaeAnomalyCount && vaeAnomalyCount > 0) {
    displayQuestions[1] = `Triage the ${vaeAnomalyCount} VAE anomalies and suggest actions`;
  }
  if (cemPoorCount && cemPoorCount > 50) {
    displayQuestions[0] = `${cemPoorCount} subscribers have poor CEM — what should we do?`;
  }

  return (
    <div className="l4-starter-questions">
      {displayQuestions.map((q, i) => (
        <button
          key={i}
          type="button"
          className="l4-suggestion"
          onClick={() => onSelect(q)}
        >
          {q}
        </button>
      ))}
    </div>
  );
}
