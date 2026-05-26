# Forecast Page — Explained in Plain Words

> For project mastery + defense. Reading time ~8 min. Assumes zero prior knowledge.
> Companion to [10_explainer.md](10_explainer.md) (Granger causality from scratch).

## The one-sentence answer to "where is the sliding window?"

**There is no sliding window in the forecast.** The Forecast page (`/predictive`) predicts the future using **Granger-causal lagged regression**, not a moving average over a window. If anyone on the jury asks "do you use a sliding/rolling window to forecast?", the honest answer is: *"No — we forecast by using a network signal that statistically leads the customer-experience signal in time."* This document explains exactly what that means and why it is better.

---

## 1. What a forecast normally means (the naive way)

The obvious way to predict the future of a number is to look at its own past and extend the trend:

> "CEM score was 0.71, 0.70, 0.69 last three months → next month ≈ 0.68."

That is **history-only extrapolation**. A *sliding window* (a.k.a. rolling window / moving average) is the classic tool here: you take the last `W` values, average them (or fit a line), slide forward one step, repeat. It is simple but has a fatal weakness for our problem:

- It only knows the **symptom** (CEM going down).
- It does **not** know the **cause** (which part of the network degraded first).
- So it can tell you *that* experience will drop, but never *why* or *what to fix*. It cannot drive an action.

**We deliberately do not use this method.** It would not support the defense story ("network problems are invisible to OSS until a customer complains").

---

## 2. What we do instead — the cause leads the symptom

Key insight: in a telecom network, the **network KPI (OSS)** degrades *before* the **customer experience (CEM)** degrades. A cell's signal quality drops today; the customer's experience score drops a few cycles later, once enough calls/sessions are affected.

So instead of forecasting CEM from its own past, we forecast it from the **past of the OSS signal that leads it**:

```
              (time delay = "best_lag")
OSS_X(t - lag) ───────────────────────────▶ CEM_Y(t)
network cause                                customer symptom
```

If we know that `OSS_X` reliably predicts `CEM_Y` with a delay of `best_lag` steps, then **today's OSS value tells us CEM `best_lag` steps into the future** — a real, explainable forecast with a named cause.

---

## 3. How the forecast is actually computed (step by step)

This is the logic in `services/api-gateway/routers/granger.py` → `GET /granger-causality/forecast`, which the page calls via `/api/granger-forecast`:

1. **Pick the proven pairs.** From the Granger analysis (notebook 10 + the live engine), take only the OSS→CEM pairs that are *Granger-significant* — meaning OSS_X has been statistically shown to predict CEM_Y (see §4). Each pair carries its `best_lag` (the delay at which the prediction is strongest).

2. **Fit a small straight-line model (OLS).** For each pair, on that area's monthly panel (`area_network_health`), fit:

   ```
   CEM_Y(t)  ≈  a  +  b · OSS_X(t − best_lag)
   ```

   `a` (intercept) and `b` (slope, shown as `β` on the page) are learned from history. `b` is the heart of it: "for every 1 unit OSS_X moves, CEM_Y moves `b` units, `best_lag` steps later."

3. **Project forward.** Take the **latest observed** `OSS_X`, push it through the fitted line, and you get the projected `CEM_Y` at time `t + best_lag`. That projected number is what the Forecast page draws as the second point of the sparkline.

4. **Report honesty signals.** The page also shows `R²` (how well the lagged line fits — high = trustworthy projection) and `β` in scientific notation. No `R²`, no projection is claimed. **No mock data, no random numbers.**

---

## 4. Why we trust the pair — Granger in one paragraph

"OSS_X Granger-causes CEM_Y" means: *adding the past of OSS_X to a model that already knows the past of CEM_Y significantly reduces the prediction error.* It is tested with an **F-test** comparing two regressions — one using only CEM's own past (restricted), one adding OSS's past (full). If the full model is significantly better (low p-value), OSS carries predictive information CEM's own history does not. That is the statistical license to forecast CEM from OSS. Full from-scratch walkthrough: [10_explainer.md](10_explainer.md).

> Caveat we state openly: Granger causality is *predictive* precedence, not proof of physical causation. It says "X reliably comes before Y," which is exactly what a forecast needs, but it is not a controlled experiment.

---

## 5. The `LAG_WINDOW_MINUTES` constant — NOT a sliding window

This name confuses people, so be precise:

- `best_lag` is a count of **steps** (rows in the panel), e.g. `best_lag = 2`.
- `LAG_WINDOW_MINUTES` (default **43200** = 30 days = 1 month) is just a **unit converter**: it turns "2 steps" into "2 × 43200 = 86,400 minutes ≈ 60 days of lead time" so the UI can say *"detected ~60 days ahead."*

It is a **multiplication constant**, not a moving-average window over data. Deploy at a finer cadence (e.g. 30s pipeline cycles) and you override it via the `LAG_WINDOW_MINUTES` env var. See [granger_two_tier.md memory] and CLAUDE.md.

---

## 6. "But CLAUDE.md mentions a Rolling Window Engine?"

That engine is **planned, not built**. It is a future *data-sampling* idea (stratified batch sampling per pipeline cycle to simulate real-time intake), and even then it would feed *ingestion*, not the forecast math. The only real sliding-window code in the repo today is a sampler unit test (`pipeline-worker/tests/test_sampler.py`), unrelated to forecasting. So: nothing on the Forecast page uses a sliding window.

---

## 7. How to read the Forecast page (defense walk-through)

| What you see | What it means |
|---|---|
| Eyebrow "Forecast · Granger causal projection" | We forecast via cause→symptom lag, not trend extrapolation |
| Each row = an OSS→CEM pair | A proven network-leads-experience relationship for that area |
| Sparkline (2 points) | left = latest observed CEM, right = projected CEM at `t + best_lag` |
| `β = …` | slope of the lagged line: how strongly the OSS cause moves the CEM symptom |
| `R²` | fit quality — how much we trust this particular projection |
| Lead-time (minutes) | `best_lag × LAG_WINDOW_MINUTES` — how far ahead we caught it |

**The defense soundbite:** *"We don't guess the future of customer experience from its own past — we read it off the network signal that we proved comes first. That turns reactive monitoring into proactive remediation, with a named cause and a measured lead time."*
