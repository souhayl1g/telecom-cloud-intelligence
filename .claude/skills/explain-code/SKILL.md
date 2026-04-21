---
name: explain-code
description: "Explain code clearly and educationally. Actions: explain, understand, walk me through, how does this work, what does this do, break down, describe. Elements: function, class, algorithm, module, pipeline, endpoint, component, query, decorator, hook, middleware. Use for: understanding unfamiliar code, onboarding, preparing presentations or defense demos, reviewing before refactoring."
---
# Explain Code — Anthropic-style Educational Breakdown

When asked to explain code, follow this structure:

## Explanation Layers (apply based on complexity)

### 1. One-Line Summary
What this code does in plain English. No jargon.

### 2. Why It Exists
The problem it solves in this codebase. Connect to business/project context when known.

### 3. How It Works — Step by Step
Walk through the logic sequentially. Use numbered steps. Reference actual line numbers or variable names from the code.

### 4. Key Design Decisions
- Why this approach was chosen over alternatives
- Notable patterns used (e.g. dependency injection, factory, async/await, generator)
- Trade-offs made

### 5. Connections
What calls this? What does this call? Where does data come from / go to?

### 6. Gotchas / Non-obvious Parts
Any behavior that could surprise a reader. Edge cases. Side effects.

## Rules

- Always quote actual code snippets when referencing specific parts
- Adjust depth to the question: "what does this do" = brief; "walk me through" = full breakdown
- For ML/AI code: explain the mathematical intuition in plain language alongside the code
- For async code: describe the execution order explicitly
- Never assume context — if the function name is ambiguous, state what you're inferring
- For this project (Telecom Cloud Intelligence): connect explanations to ADN, CEM, OSS/BSS, pipeline stages where relevant

## Output Format

Use headers for each layer. Keep each section concise. Prefer bullet points over paragraphs for the step-by-step.

For short functions (< 20 lines): skip headers, use flowing explanation.
For long/complex code: use full structured breakdown.
