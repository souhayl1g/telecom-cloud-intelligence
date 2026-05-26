# Notebook 00 — Plain-Language Explainer

> Audience: you (Souhayl) preparing for thesis defense.
> Goal: explain EVERY data-science concept used in notebook 00 in plain language. No jargon without definition.

---

## What is this notebook for?

It is **Exploratory Data Analysis (EDA)** — the first step in any data science project. Before you train models, before you clean data, you LOOK at the data. You stare at distributions, count NaNs, plot correlations, and ask "what is this data actually telling me?"

This is **CRISP-DM Phase 2 — Data Understanding**. CRISP-DM is a 6-phase methodology: Business Understanding → Data Understanding → Data Preparation → Modeling → Evaluation → Deployment. We are in phase 2.

---

## Concepts Used (in order of appearance)

### 1. Reproducibility & Seeds

**SEED = 42.** A "seed" tells random number generators where to start. Without a seed, every notebook run produces different samples / random splits. With a fixed seed, results are byte-identical across runs. This is REQUIRED for thesis defense — reviewers must be able to re-run your notebook and get the same numbers.

We set the seed for: `numpy`, `random`, `PYTHONHASHSEED` (Python's internal hashing).

---

### 2. Skewness & log1p

**Problem:** Most network/traffic data is "skewed right" — most subscribers use little data, a few use a LOT. If you plot a histogram, it looks like everything is in one tiny bar on the left and a huge empty space on the right. Useless visually.

**Skewness** measures how lopsided a distribution is.
- Skew ≈ 0 → symmetric (like a bell curve)
- Skew > 0 → tail on the right (most values low, few very high) — typical for traffic, money, populations
- Skew < 0 → tail on the left (rare)
- |Skew| > 1 → "highly skewed" (Bulmer 1979, standard textbook cutoff)

**log1p transform:** `log1p(x) = log(1 + x)`. It compresses big values and stretches small ones. After applying log1p to skewed data, the histogram becomes readable — the bell curve shape emerges.

Why `1 + x` instead of just `log(x)`? Because `log(0)` is undefined. `log1p(0) = log(1) = 0` is safe.

**Our rule:** If `|skew| > 1.0` AND column is non-negative → plot on log1p axis. Otherwise plot raw.

---

### 3. Missingness: NaN, MAR, MCAR, MNAR

**NaN = Not a Number** = missing value. Pandas marks empty cells as NaN.

There are three theoretical types of missingness (Little & Rubin 2002):

- **MCAR (Missing Completely At Random):** missingness has nothing to do with anything. Like a random sensor glitch. Safe to drop.
- **MAR (Missing At Random):** missingness depends on OTHER observed columns. E.g., `volte_flag` is NaN whenever `generation = 2G` (because 2G doesn't support VoLTE). Can be imputed using the other columns.
- **MNAR (Missing Not At Random):** missingness depends on the value itself. E.g., people who churned refused to fill the survey. Hardest case — biases the model.

**missingno** library (3.5k+ GitHub stars by ResidentMario):
- `msno.bar(df)` — count of NON-missing values per column
- `msno.matrix(df)` — row-wise picture; **vertical white stripes** mean "always missing together" — a MAR signal
- `msno.dendrogram(df)` — hierarchical clustering of columns by co-missingness; **columns clustered close together are missing in the same rows**

This is much better than `seaborn.heatmap(df.isna())` because the dendrogram reveals the MECHANISM behind missingness, not just where it is.

---

### 4. Pearson vs Spearman vs Mutual Information

Three different ways to measure "does feature X relate to feature Y?".

**Pearson correlation** (most common):
- Range: -1 to +1
- Measures LINEAR relationships only
- Sensitive to outliers
- "If X doubles, does Y double too?"

**Spearman correlation** (rank-based, Spearman 1904):
- Range: -1 to +1
- Measures MONOTONIC relationships (always increasing or always decreasing, but not necessarily linear)
- Robust to outliers (converts values to ranks first)
- "If X goes up, does Y go up too — regardless of by how much?"

**Mutual Information** (Reshef et al. 2011):
- Range: 0 to ∞ (in "nats", a unit from information theory)
- Measures ANY statistical dependence — including U-shapes, sinusoids, anything Pearson misses
- "How many bits of Y can I predict if I know X?"
- Computed via `sklearn.feature_selection.mutual_info_regression`

**Our rule:** Look at all three together.
- If Pearson AND Spearman both high → strong linear relationship
- If Spearman high but Pearson low → monotonic non-linear (LightGBM will catch this)
- If MI high but Spearman low → non-monotonic relationship (XGBoost / VAE will catch this)
- If all three low → feature is unrelated to target; can drop

---

### 5. KDE (Kernel Density Estimate)

A KDE is a SMOOTH histogram. Instead of stacking bars, it draws a smooth curve representing the probability that the variable takes each value.

- `sns.histplot(s, kde=True)` plots both histogram AND KDE
- `sns.kdeplot(s)` plots only the smooth curve
- Used for OVERLAY plots — two histograms overlap into one ugly mess; two KDEs overlap into one clear pair of curves

We use KDE overlays to compare:
- Real vs simulated distributions (§10)
- Distribution-vs-target (§22.5)

---

### 6. Quartiles & Distribution-vs-Target

A **quartile** divides the data into 4 equal-sized buckets:
- Q1 = bottom 25%
- Q2 = next 25% (between 25% and 50% = median)
- Q3 = next 25% (between 50% and 75%)
- Q4 = top 25%

**Distribution-vs-target pattern:** Split data into target quartiles, then overlay KDEs of each feature for each quartile. If a feature's KDE looks different in Q1 vs Q4 → that feature SEPARATES high-target from low-target subscribers → it's a good predictor.

If the KDEs all overlap → the feature is uninformative; the model will not benefit from it.

We use `dou_total` (data usage) as a PROXY for CEM score because the true `cem_score` is computed only in notebook 01.

---

### 7. IQR (Interquartile Range) & Outliers

**IQR = Q3 − Q1** (middle 50% of the data).

**Tukey's outlier rule:** A point is an outlier if it's < `Q1 − 1.5·IQR` or > `Q3 + 1.5·IQR`. This is shown by boxplot "whiskers" and dots beyond them.

We REPORT outlier % per column but do NOT remove them — that's notebook 01's job (Winsorize at p99).

**Violin plots + z-score (§12.5).** A **violin** is a box plot with a mirrored KDE wrapped around it — its *width* shows where data is dense, exposing multi-modal humps a box plot hides. The **z-score rule** flags any point with `|z| > 3` (more than 3 standard deviations from the mean) — the *symmetric/Gaussian* outlier rule. We print it beside the IQR % so you can see how right-skew inflates the symmetric count: on heavy-tailed traffic, z-score and IQR disagree, and IQR (skew-robust) is the one we trust.

---

### 8. Kolmogorov-Smirnov (KS) Test

**Problem:** We have real BSS data for Feb + Mars 2026 and bootstrap-simulated data for the other 7 months. Did the simulator preserve the real distribution, or did it drift?

**Visual check:** overlay KDEs. Easy but subjective.

**Statistical check:** KS test (Massey 1951).
- Null hypothesis (H0): the two samples come from the SAME distribution.
- Computes the maximum gap D between the two cumulative distribution functions (CDFs).
- Returns a p-value: probability of observing this gap if H0 is true.
- If p < alpha (we use 0.05) → reject H0 → distributions DIFFER.

**The trap (Massey 1951):** With many samples (N=50K), even tiny differences become "statistically significant" (p < 0.05). So we ALSO report EFFECT SIZE (D):
- D < 0.1 → small drift (probably fine)
- 0.1 < D < 0.2 → medium drift (investigate)
- D > 0.2 → large drift (simulator broken)

**`scipy.stats.ks_2samp(a, b)`** does the math.

---

### 9. Choropleth (Geographic Visualization)

A **choropleth** is a map where each region is colored by a value. We use:
- `dashboard/lib/tunisia-geojson.json` — 24 governorates (ADM1 boundaries) as polygons
- `geopandas` — pandas extended with geometry columns
- `gdf.plot(column='subscribers', cmap='YlOrRd')` — colors each governorate by subscriber count

**Why this matters for defense:** "We have 968K real subscribers" is abstract. "Tunis has 200K, Sfax has 150K, Tataouine has 4K" is concrete and obvious to a Tunisian audience.

---

### 9.5 Telecom Cell Topology Graph (networkx)

This is the "custom network-research visualization." Instead of yet another bar chart, we draw the network as a **graph** — dots connected by lines — so the jury *sees* its structure.

- **Node** = a Tunisia area (governorate-level roll-up of cells).
- **Edge** = drawn only when two areas' KPI profiles are strongly similar — Pearson correlation above `TOPO_CORR_THRESHOLD = 0.70`. The threshold keeps the picture from becoming a "hairball"; only meaningful links survive.
- **Layout** = `spring_layout` (Fruchterman–Reingold, force-directed): pretend every edge is a spring pulling its two nodes together and every node is a magnet pushing others away, then let the system settle. Similar areas end up physically close; odd ones drift to the edge.

**Why a graph for telecom?** A flat "KPI per area" table hides relationships. A force-directed graph reveals which parts of the network *move together* — regions sharing load/infrastructure patterns cluster, while an area whose network behaves unlike everyone else's sits alone, far from the blob. Force-directed graphs are the standard way operators and network researchers visualize cell/site relationships.

**How to read it:** tight cluster = correlated regions; long bridge = weakly-linked areas; a lone node far from the crowd = anomalous behavior worth investigating.

**Defense soundbite:** *"We don't just list KPIs per governorate — we render the network's correlation structure as a graph, so you can see at a glance which regions are coupled and which one stands alone."*

---

### 10. Stratified Sampling

When you sample 100K rows from 8M, do you want a random 100K? Or do you want PROPORTIONAL representation of real and simulated rows?

**Stratified sampling:** group by some column (e.g., `source_origin`), then take a proportional sample from each group. Ensures every category is represented.

```python
df.groupby('source_origin').sample(n=50_000, random_state=SEED)
```

Used for MI computation (§14) so both real and simulated rows feed the estimator.

---

### 11. Why we did NOT use ydata-profiling / sweetviz

Both are popular "one-line EDA" tools that produce 50-page HTML reports. They're great for quick exploration. But for a DEFENSE notebook, they're a black box — reviewers can't see WHY each diagnostic was chosen. We chose explicit, cited diagnostics instead so each step has methodology justification.

---

## Glossary (quick reference)

| Term | One-line definition |
|---|---|
| EDA | Exploratory Data Analysis — look at the data before modeling |
| CRISP-DM | 6-phase data-mining methodology (we're in Phase 2) |
| Seed | Starting point for random number generator (= reproducibility) |
| Skew | How lopsided a distribution is (>1 = heavy right tail) |
| log1p | `log(1+x)` — compresses heavy tails for visualization |
| NaN | Not a Number — missing value |
| MCAR / MAR / MNAR | The 3 types of missingness (random / dependent / value-based) |
| Pearson | Linear correlation, −1 to +1 |
| Spearman | Rank correlation — monotonic, robust to outliers |
| Mutual Information | Any statistical dependence including non-linear |
| KDE | Smooth histogram (kernel density estimate) |
| Quartile | 25% bucket (Q1=bottom, Q4=top) |
| IQR | Q3 − Q1 (middle 50% spread) |
| KS test | Statistical test: do two samples come from the same distribution? |
| Effect size D | KS statistic — max CDF gap; small <0.1, large >0.2 |
| Choropleth | Map colored by a numeric value per region |
| Network graph (networkx) | Areas as nodes, strong-correlation links as edges |
| spring_layout | Force-directed placement — similar nodes cluster, odd ones drift out |
| Stratified sample | Sample proportionally from each group |
| Papermill | Tool to run a notebook with parameter overrides (used by retrain container) |

---

## How to read the notebook in 5 minutes

1. **§0 (constants):** SLA thresholds, seed, sampling sizes. Memorize: integrity 98%, CDR 2%, seed 42, |skew|>1 → log1p.
2. **§3 (BSS load):** 8M rows total. 968K real (Feb+Mars), 7M simulated. Warning about `_consistent` double-load.
3. **§7 + §8 (missingness):** `sim_slot` 60% NaN, `churned` 56% NaN, `volte_flag` 55% NaN. Dendrogram clusters them — they're MAR (missing together when subscriber is 2G).
4. **§14 (correlations):** Three views — Pearson (linear), Spearman (monotonic), MI (non-linear). Look for non-overlap → non-linear relationships LightGBM will exploit.
5. **§22.5 (dist-vs-target):** Which features separate heavy-data-users from light-data-users? Those will dominate CEM-score prediction.
6. **§23 (choropleth):** Tunis / Sfax / Sousse dominate. Defense talking point.
7. **§24 (KS):** Statistical evidence that simulator drift is small (D mostly < 0.1).
8. **§26 (Limitations):** Known caveats — read this BEFORE the defense Q&A.
9. **§27 (Sources):** Every methodology has a citation.

That is the entire notebook in 9 bullets.
