---
name: nexo-bss-simulator
description: Generate realistic BSS subscriber data for Telecom NeXoligence. Use when: (1) simulating new BSS months from real TT data, (2) creating bootstrap-resampled datasets with temporal drift, (3) generating OSS cell KPIs correlated with BSS area profiles, (4) computing subscriber features and area health aggregates, (5) validating data distributions against real data.
---

# NeXo BSS Simulator

Generate simulated telecom subscriber data that preserves real-world statistical properties while adding privacy-preserving perturbation and temporal drift.

## Core Workflow

### 1. Bootstrap BSS Generation

Use `scripts/generate_bss_months.py` or replicate its logic:

```python
# Load real data (Feb + Mar = 968K rows)
real_df = pd.concat([pd.read_csv("TT_data/BSS/smartcare_cem_feb.csv"),
                     pd.read_csv("TT_data/BSS/smartcare_cem_mars.csv")])

# Sample with replacement
batch = real_df.sample(n=500_000, replace=True)

# Perturb numericals: multiply by exp(N(0, 0.06))
for col in ["dou_total", "traffic_2g", "traffic_3g", "traffic_4g", "traffic_5g",
            "duration", "voice_onlinetime_3g", "voice_onlinetime_2g"]:
    batch[col] = (batch[col] * np.exp(np.random.normal(0, 0.06, len(batch)))).round().astype(int)
```

### 2. Month Drift Parameters

| Month | DOU Factor | 5G Factor | Silent Shift | 5G Migration |
|---|---|---|---|---|
| Jan | 0.88 | 0.65 | -0.03 | 5G→4G demotion 8% |
| Apr | 1.18 | 1.35 | +0.04 | 4G→5G promotion 12% |
| May | 1.35 | 1.65 | +0.08 | 4G→5G promotion 12% |

### 3. Identity Replacement

- IMSI: `60502` + 10 random digits
- TAC: 15 random digits
- Never reuse real IMSI/TAC values

### 4. DOU Guard

If `traffic_2g + traffic_3g + traffic_4g + traffic_5g > 1.5 * dou_total`, raise `dou_total` to traffic sum.

### 5. OSS Simulation

Use `services/data-ingest/simulate_oss.py`:
- 24 areas × 10 cells × 5 months = 1200 cell records
- Correlates with BSS area profiles (sub_count, pct_data, pct_legacy_sim)
- Month drift: latency increases, throughput decreases over time

## Validation Checklist

- [ ] Row count matches target (500K per month)
- [ ] All 26 columns present
- [ ] month_year set correctly
- [ ] No real IMSI/TAC values leaked
- [ ] DOU >= traffic sum for all rows
- [ ] Categorical distributions match real data (±5%)

## Key Files

- `services/data-ingest/generate_bss_months.py` — Main generator
- `services/data-ingest/simulate_oss.py` — OSS generator
- `services/data-ingest/compute_features.py` — Feature computation
- `services/data-ingest/ingest_bss.py` — Real data loader
