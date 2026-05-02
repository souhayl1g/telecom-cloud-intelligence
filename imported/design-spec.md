# NeXo Dashboard — Design Specification

> **Version:** 1.0 · **Stack:** Next.js 14 + React 18 + TypeScript · **Theme engine:** Pure CSS custom properties (no Tailwind)
> **Last updated:** 2026-04-28 · **Owner:** Souhayl Guenichi

---

## 1. Project Identity

| Field | Value |
|-------|-------|
| **Product name** | NeXo — Telecom Cloud Intelligence |
| **Client** | Tunisie Telecom (TT) |
| **Platform** | Huawei ADN (Autonomous Driving Network) |
| **User** | NOC operator / telecom AI engineer — monitors screens for long shifts |
| **Context** | Real-time OSS+BSS convergence intelligence, ML anomaly detection, ADN L4 autonomous operations |
| **Design goal** | Maximum information density at zero visual noise. Every pixel serves the operator. |

---

## 2. Design System

### 2.1 Color Tokens

All values live in `dashboard/app/globals.css` under `:root`. **Never hardcode hex values** — always reference CSS variables.

#### Background Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-root` | `#0A0F1C` | Page background (dark OLED) |
| `--bg-surface` | `rgba(255,255,255,0.03)` | Cards, panels |
| `--bg-elevated` | `rgba(255,255,255,0.06)` | Dropdowns, modals, popovers |
| `--bg-hover` | `rgba(255,255,255,0.05)` | Row/item hover |

#### Text Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--text-primary` | `#E8ECF1` | Headings, labels |
| `--text-secondary` | `#8494A7` | Descriptions, metadata |
| `--text-muted` | `#546478` | Timestamps, disabled |

#### Border Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--border` | `rgba(255,255,255,0.08)` | Card borders, dividers |
| `--border-active` | `rgba(255,255,255,0.16)` | Focused inputs, active tabs |

#### Brand Identity

| Token | Value | Brand |
|-------|-------|-------|
| `--color-primary` | `#C7000B` | Huawei crimson |
| `--color-secondary` | `#E30613` | Tunisie Telecom red |
| `--color-accent` | `#F08A24` | TT sunset orange |
| `--gradient-brand` | `135deg, #F08A24, #E30613, #C7000B` | Primary CTA gradient |
| `--gradient-tt` | `135deg, #F08A24, #E30613` | Secondary gradient |

#### Semantic States

| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `#34D399` | Healthy, passing, auto-approved |
| `--color-warning` | `#FBBF24` | Degraded, pending approval |
| `--color-danger` | `#EF4444` | Critical anomaly, rejected, error |
| `--color-info` | `#00A9CE` | Informational, info actions |
| `--color-purple` | `#8B5CF6` | AI/ML events, model outputs |

#### Semantic Background + Border Pairs (use together)

```css
/* Success */
background: rgba(52, 211, 153, 0.10);
border: 1px solid rgba(52, 211, 153, 0.22);

/* Warning */
background: rgba(251, 191, 36, 0.10);
border: 1px solid rgba(251, 191, 36, 0.22);

/* Danger */
background: rgba(239, 68, 68, 0.10);
border: 1px solid rgba(239, 68, 68, 0.22);

/* Info */
background: rgba(0, 169, 206, 0.10);
border: 1px solid rgba(0, 169, 206, 0.22);

/* Purple (AI) */
background: rgba(139, 92, 246, 0.10);
border: 1px solid rgba(139, 92, 246, 0.22);
```

---

### 2.2 Typography

| Role | Font | Weights | Notes |
|------|------|---------|-------|
| **Headings / Metric values** | Fira Code | 400, 500, 600, 700 | Monospace — equal-width digits for live updating numbers |
| **Body / UI labels** | Fira Sans | 300, 400, 500, 600, 700 | Clean, legible at small sizes |

**Google Fonts import (add to `globals.css`):**
```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
```

#### Type Scale

| Level | Element | Font | Size | Weight | Line-height |
|-------|---------|------|------|--------|-------------|
| Display | Hero KPI | Fira Code | 2.5rem | 700 | 1.1 |
| H1 | Page title | Fira Code | 1.5rem | 600 | 1.2 |
| H2 | Section heading | Fira Code | 1.125rem | 600 | 1.3 |
| H3 | Card title | Fira Sans | 0.9375rem | 600 | 1.4 |
| Body | Descriptions | Fira Sans | 0.875rem | 400 | 1.6 |
| Caption | Timestamps, meta | Fira Sans | 0.75rem | 400 | 1.5 |
| Badge | Status labels | Fira Sans | 0.6875rem | 500 | 1 |

> **Rule:** Body text minimum 14px. Never go below 12px for any visible text. Line-length cap: 72 characters.

---

### 2.3 Spacing

8px base grid. All spacing in multiples of 4px.

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | `4px` | Inline gap, icon padding |
| `--space-2` | `8px` | Small gap between elements |
| `--space-3` | `12px` | Card inner padding (compact) |
| `--space-4` | `16px` | Standard card padding |
| `--space-6` | `24px` | Section gap |
| `--space-8` | `32px` | Large section padding |

---

### 2.4 Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `6px` | Badges, tags, inputs |
| `--radius-md` | `10px` | Cards, buttons |
| `--radius-lg` | `14px` | Modals, large panels |
| `--radius-xl` | `18px` | Feature cards |
| `--radius-full` | `999px` | Pills, avatars, toggle |

---

### 2.5 Transitions

```css
/* Standard: all state changes */
transition: var(--transition); /* 0.2s cubic-bezier(0.4, 0, 0.2, 1) */

/* Fast: hover color/opacity */
transition: color 150ms ease, background 150ms ease, border-color 150ms ease;

/* Slow: panel open/close */
transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1), opacity 300ms ease;
```

---

### 2.6 Shadows & Glow Effects

```css
/* Card resting */
box-shadow: 0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px var(--border);

/* Card hover */
box-shadow: 0 4px 16px rgba(0,0,0,0.5), 0 0 0 1px var(--border-active);

/* Brand glow (CTA buttons on hover) */
box-shadow: 0 0 20px rgba(199, 0, 11, 0.35);

/* Success glow (health indicator) */
box-shadow: 0 0 10px rgba(52, 211, 153, 0.4);

/* Danger glow (critical anomaly) */
box-shadow: 0 0 12px rgba(239, 68, 68, 0.45);
```

---

## 3. Component Library

### StatusBadge

```
Shape: pill (border-radius: var(--radius-full))
Size: 6px × 6px dot + label text (Fira Sans 0.6875rem, 500)
States: success | warning | danger | info | purple | muted
```

Usage: anomaly severity, pipeline status, action status, model health

---

### KPICard

```
Layout: 2-row vertical
  Row 1: icon (24px SVG) + label (Fira Sans, secondary color)
  Row 2: metric value (Fira Code 2.5rem, 700) + unit (Fira Sans, muted)
  Row 3 (optional): trend arrow + delta % (colored)
Background: var(--bg-surface)
Border: 1px solid var(--border)
Radius: var(--radius-lg)
Padding: 20px 24px
```

---

### SparklineWidget

```
Mini SVG line chart, no axes, no labels
Height: 40px, width: 100%
Line color: var(--color-info) — normal | var(--color-danger) — anomaly
Fill: 10% opacity of line color
Used inside: KPICard (bottom), Overview grid, L4 Live Monitor
```

---

### AnomalyMarker

```
On line charts: circle marker at anomaly timestamp
Normal data: solid line #0080FF
Anomaly marker: red circle (#EF4444) + tooltip on hover
Annotation text: "ANOMALY" badge in danger semantic pair
```

---

### L4ActionCard

```
Layout: horizontal
  Left: action type icon (SVG 20px) + title (H3) + description (body)
  Right: confidence badge + approve/reject buttons
Status variants:
  pending → brand-gradient Approve button + outlined Reject
  approved → success badge + "Executed" label
  rejected → danger badge + "Rejected" label
  auto_approved → info badge + "Auto-approved" label
```

---

### AlertToast

```
Fixed position: bottom-right, 16px inset
Width: 320px
Stack order: newest on top
States: warning (yellow border) | danger (red border) | info (cyan border)
Dismiss: X button top-right
Click behavior: navigates to relevant page tab
Animation: slide-in from right 300ms, fade-out on dismiss 200ms
```

---

### LivePulse

```
Animated concentric ring around status dot
Color: matches severity (success = green, danger = red)
Animation: scale 1 → 1.6, opacity 1 → 0, duration 2s, infinite
Used on: L4 Agent nav link, active pipeline run indicator
```

---

## 4. Page-by-Page Layout Specs

### `/overview` — Platform Overview

**Purpose:** Single-screen health snapshot of the entire platform.

**Layout:** Fixed top nav → 4-column KPI strip → 2-column grid (charts left, model health right) → recent activity feed

**KPI Cards (row of 4):**
- Pipeline runs (24h)
- Active anomalies
- SLA risk score (latest)
- Subscribers processed

**Charts:**
- Primary: Donut — model health (3 models, colored by health state)
- Secondary: Sparkline per KPI card

**Components:** KPICard × 4, SparklineWidget × 4, StatusBadge, DonutChart

---

### `/anomalies` — OSS Anomaly Browser

**Purpose:** Browse and investigate detected OSS network anomalies.

**Layout:** Filter bar (severity, date range, area) → anomaly table → detail panel (slide-in right)

**Charts:**
- Primary: Line chart with AnomalyMarker — timeline of KPI values with anomaly events highlighted
- Secondary: Heatmap grid — anomaly density by hour × day

**Color guidance:**
- Normal line: `#0080FF`
- Anomaly point: `#EF4444` circle + danger glow
- Heatmap: cool blue (low density) → hot red (high density)

**Components:** AnomalyMarker, StatusBadge, Heatmap, DetailPanel

---

### `/sla-risk` — SLA Risk Scores

**Purpose:** Track SLA breach probability over time per pipeline run.

**Layout:** Score summary strip → time-series chart → explanation table (top features)

**Charts:**
- Primary: Line + confidence band — actual SLA score (solid) + forecast band (dashed + shaded)
- Secondary: MetricBar — top 6 feature importances (horizontal bars)

**Threshold lines:** 0.7 = warning (yellow dashed), 0.9 = critical (red dashed)

**Components:** KPICard (latest score + trend), MetricBar, ConfidenceBand chart

---

### `/correlations` — OSS-BSS Correlation Explorer

**Purpose:** Visualize relationships between network KPIs and subscriber experience.

**Layout:** Correlation matrix (heatmap) top → selected pair scatter plot bottom

**Charts:**
- Primary: Heatmap matrix — correlation coefficient grid (blue negative, red positive, divergent scale)
- Secondary: Scatter plot with regression line for selected pair

**Color:** Divergent — `#0080FF` (strong negative) → `#F8FAFC` (zero) → `#EF4444` (strong positive)

**Components:** HeatmapMatrix, ScatterPlot, CorrelationBadge (r value + p-value)

---

### `/intelligence` — AI Intelligence Hub

**Purpose:** High-level AI insights across all models + operator natural language queries.

**Layout:** 3-column card grid (one per model insight) + query input at bottom

**Components:** IntelCard (model + insight + confidence), QueryInput (Fira Code monospace), ResponseBubble

---

### `/predictive` — Forecast & Predictive Analytics

**Purpose:** Time-series forecast of anomaly volume and network degradation.

**Layout:** Metric selector tabs → forecast chart → forecast table

**Charts:**
- Primary: Line + confidence band — actual (solid `#0080FF`) + forecast (dashed `#F08A24`) + uncertainty band (shaded 15% opacity)
- Secondary: Area chart — trend history (fill 20% opacity)

**Legend:** always shown, distinguishes actual vs forecast clearly

---

### `/topology` — Network Topology

**Purpose:** Visual map of network cells and their current health state.

**Layout:** Full-screen network graph + sidebar (node detail panel)

**Charts:**
- Primary: Network graph (d3-force) — nodes = cells, edges = connections
- Node color: severity overlay (success/warning/danger by CSS variable)
- Edge color: `#90A4AE` at 60% opacity

**Accessibility note:** Provide adjacency list table as alternative (toggle button)

---

### `/capacity` — Capacity Planning

**Purpose:** Show resource headroom per KPI dimension.

**Layout:** KPI summary row → horizontal bar charts per resource → headroom table

**Charts:**
- Primary: Horizontal bar (headroom %) — green > 40%, yellow 15-40%, red < 15%
- Secondary: Gauge (current utilization) — semicircle gauge per resource

---

### `/data-warehouse` — Data Lake Explorer

**Purpose:** Browse MinIO data lake layers (raw / processed / curated).

**Layout:** Layer tabs (Raw | Processed | Curated) → object table → schema preview panel

**Components:** LayerBadge, ObjectRow, SchemaViewer (JSON tree)

---

### `/pipeline-runs` — Pipeline Execution History

**Purpose:** Track each 2-minute pipeline cycle: status, duration, records processed.

**Layout:** Status summary row → timeline list → run detail drawer

**Charts:**
- Primary: Timeline (Gantt-style) — pipeline steps as colored horizontal bars per run
- Secondary: Status bars — pass/fail ratio over last 50 runs

**Status colors:** completed = success, failed = danger, running = info + LivePulse

---

### `/ops-metrics` — Operational Health

**Purpose:** Service-level health of all 8 platform components.

**Layout:** Service grid (2 columns) → per-service detail (latency, uptime, errors)

**Charts:**
- Primary: Line chart per service (p50/p95 latency)
- Secondary: StatusBadge per service (healthy / degraded / down)

---

### `/model-evaluation` — ML Model Metrics

**Purpose:** Real evaluation metrics from trained models in `notebooks/`.

**Layout:** Info banner → regression section → anomaly section → radar comparison

**Charts:**
- MetricBar: R², MAE, RMSE per regression model
- ConfusionMatrix: 2×2 heatmap grid (TN/FP/FN/TP)
- RadarChart: Pentagon — 5-axis model comparison
- FeatureImportanceChart: horizontal bars (top 6 features)

**All charts are custom SVG — no external chart library.**

---

### `/l4-agent` — ADN L4 Autonomous Ops Agent

**Purpose:** Huawei ADN Level 4 autonomous operations — chat, action approval, live monitor.

**Layout:** Three-tab panel (tabs always visible on desktop):
- **Tab 1 — Agent Chat:** Conversation with Qwen2.5:7b, streaming responses, code-block rendering
- **Tab 2 — Actions:** Pending actions (approve/reject) + auto-approved list
- **Tab 3 — Live Monitor:** MiniSparkline × 4 + DonutChart + system metrics

**Components:** L4ActionCard, AlertToast, LivePulse (on tab nav link), StreamingAreaChart, DonutChart

**CSS critical rules:**
```css
/* Tabs always visible — do NOT add display:none to .l4-tabs */
.l4-tabs { display: flex; flex-shrink: 0; }
.l4-chat-panel, .l4-actions-panel { display: none; }
.l4-panel-active { display: flex !important; }
```

---

### `/login` · `/signup` — Authentication Pages

**Purpose:** JWT + OAuth2 login/register.

**Layout:** Centered card on full `--bg-root` background — brand gradient header strip, form body, OAuth buttons

**Components:** AuthCard, OAuthButton (Google/GitHub), InputField with inline error, BrandGradientStrip

---

## 5. Chart Type Map

| Page | Primary Chart | Secondary Chart | Library |
|------|--------------|-----------------|---------|
| overview | KPI cards + sparklines | Donut | Custom SVG |
| anomalies | Line + AnomalyMarker | Heatmap grid | Recharts v2.15.3 |
| sla-risk | Line + confidence band | MetricBar | Custom SVG |
| correlations | Heatmap matrix | Scatter + regression | Recharts v2.15.3 |
| intelligence | Card grid | — | — |
| predictive | Line + confidence band | Area (history) | Recharts v2.15.3 |
| topology | Network graph | — | D3-force |
| capacity | Horizontal bar | Gauge | Custom SVG |
| data-warehouse | Table | — | — |
| pipeline-runs | Timeline / Gantt | Status bars | Custom SVG |
| ops-metrics | Line (latency) | StatusBadge | Recharts v2.15.3 |
| model-evaluation | RadarChart + ConfusionMatrix | FeatureImportance | Custom SVG |
| l4-agent | StreamingArea | Donut | Custom SVG |

> **Recharts pinned at v2.15.3.** Do NOT upgrade to v3.x — causes React error #310.
> **Custom SVG charts** live in `dashboard/components/` — no extra dependencies.

---

## 6. Animation Guidelines

| Element | Duration | Easing | Property |
|---------|----------|--------|----------|
| Card hover | 150ms | ease | background, border-color, box-shadow |
| Button hover | 150ms | ease | background, box-shadow |
| Panel open/close | 300ms | cubic-bezier(0.4, 0, 0.2, 1) | transform, opacity |
| Toast enter | 300ms | cubic-bezier(0.4, 0, 0.2, 1) | translateX, opacity |
| Toast exit | 200ms | ease-in | opacity, translateX |
| LivePulse ring | 2s | ease-out | scale, opacity (infinite) |
| Streaming area | — | — | real-time data push, no transition |
| Tab switch | 200ms | ease | opacity |
| Anomaly marker | 400ms | ease-out | scale (pop on enter) |

> **Respect `prefers-reduced-motion`:** Wrap all animations in `@media (prefers-reduced-motion: no-preference)`.
> Use `transform` + `opacity` only — never animate `width`, `height`, or `margin`.

---

## 7. Accessibility Requirements

| Rule | Requirement |
|------|------------|
| Color contrast | Minimum 4.5:1 for body text; 3:1 for large text (WCAG AA) |
| Focus rings | Visible on all interactive elements — use `outline: 2px solid var(--color-info)` |
| Keyboard nav | Tab order matches visual order. Modal/drawer traps focus. |
| ARIA labels | All icon-only buttons carry `aria-label`. Status badges carry `role="status"`. |
| Images | All `<img>` have `alt`. Chart SVGs have `role="img"` + `aria-label`. |
| Form inputs | Every `<input>` paired with `<label for="">`. Errors rendered near field, not just in color. |
| Topology fallback | Network graph: provide adjacent list table, toggle with button. |
| Color not sole indicator | Anomalies: marker shape + color. Severity: badge text + color. |
| Button type | All `<button>` carry explicit `type="button"` or `type="submit"`. |

---

## 8. NeXo Differentiators — Design Contracts

These are the visual + UX elements that make NeXo unique. Stitch must preserve them.

### Brand Gradient as Trust Signal
The `--gradient-brand` (orange→red→crimson) appears only on:
- Primary CTA buttons (Approve in L4 Agent)
- Page header accent strip
- Login/signup card header

Never use it as a background fill on large surfaces — it must feel scarce and authoritative.

### L4 Agent Approval Flow
The visual language of the approval workflow must communicate authority:
- **Pending** cards: neutral surface + amber left-border `--color-warning`
- **Approved** cards: success semantic pair background + green check
- **Rejected** cards: danger semantic pair background + red X
- **Auto-approved**: info semantic pair + "⚡ Auto" badge (SVG lightning icon)

### OSS+BSS Convergence Badge
On the Correlations and Overview pages, show a convergence indicator — a two-circle overlapping badge labeled "OSS ∩ BSS" using brand gradient fill. This signals the unique O+B data join that differentiates NeXo from single-domain tools.

### Monospace Metric Precision
All live-updating numerical values use `font-family: 'Fira Code', monospace`. This prevents layout shift as digits change in real time — equal-width characters mean the container width stays stable.
