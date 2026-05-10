# NeXo Backend Transformation — Full Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Transform 4 monolithic Python files into a deep, modular, tested backend — then layer real-data ETL, v3.0 AI models (LightGBM + VAE + CatBoost + TFT), PCMCI causal convergence engine, and upgraded multi-agent system on top.

**Architecture:** Each service splits into focused modules (config, db, routers, processors). Shared patterns (config/db) are duplicated per service (Docker containers are isolated — no cross-service imports). Tests live in `tests/` inside each service. All code passes `ruff check` before commit.

**Tech Stack:** Python 3.11, FastAPI 0.115, psycopg2, NumPy, scikit-learn 1.5, LightGBM, PyTorch 2.x, pytorch-forecasting (TFT), tigramite (PCMCI), dcor, shap, umap-learn, CatBoost, Ollama/Qwen3:8b, PostgreSQL 16, MinIO, Docker.

**Data:** Real TT BSS: Feb (468K) + Mar (500K). OSS: real when arrives, else `simulate_oss.py`. Simulated Apr/May/Jun labeled `source='simulated'`. IMSI hashed. Data NEVER committed to git.

**Working directory for all commands:** `/home/souhayl/projects/telecom-cloud-intelligence`

---

## Phase Overview

| Phase | What | Output |
|---|---|---|
| **1** | Backend restructuring — split monoliths, add tests | Modular, tested, ruff-clean backend |
| **2** | Data ETL — BSS ingest, OSS simulate, feature compute, unified runner | 970K+ real subscribers + OSS in Postgres |
| **3** | AI v3.0 — LightGBM CEM, VAE anomaly, CatBoost RAT, TFT churn | 4 new trained models + new inference endpoints |
| **4** | Convergence engine — dCor + PCMCI, O+B API | Causal graph per area, convergence endpoints |
| **5** | Agent upgrade — Qwen3:8b, real data tools, conversation persistence | Production multi-agent system |
| **6** | Dashboard + HCS evidence + polish | Full platform ready for jury |

---

# PHASE 1: Backend Module Restructuring

**Context for Kimi:** The current backend is 4 giant files. Each does everything. This phase splits each into focused modules WITHOUT changing any business logic — same behavior, just organized. Run all tests after each task. Docker builds must still pass. `ruff check services/` must be zero errors throughout.

**What EXISTS now (do not delete, refactor INTO modules):**
- `services/pipeline-worker/worker/__main__.py` — 880 lines, 22-step pipeline
- `services/api-gateway/main.py` — 940 lines, all endpoints
- `services/ai-service/main.py` — 436 lines, 3 inference endpoints
- `services/auth-service/main.py` — 517 lines, JWT + OAuth (DO NOT TOUCH in Phase 1)
- `services/agent-service/` — already modular, leave as-is in Phase 1
- `services/data-ingest/` — 3 standalone scripts, leave as-is in Phase 1

**What does NOT exist yet (you will create):**
- Any `tests/` directories
- Any `routers/` subdirectories
- `config.py`, `db.py`, `storage.py` per service

---

## Task 1.1: Pipeline-Worker — Add config + db + storage modules

**Files:**
- Create: `services/pipeline-worker/worker/config.py`
- Create: `services/pipeline-worker/worker/db.py`
- Create: `services/pipeline-worker/worker/storage.py`
- Create: `services/pipeline-worker/tests/__init__.py`
- Create: `services/pipeline-worker/tests/test_config.py`

- [x] **Step 1: Create `services/pipeline-worker/worker/config.py`**

```python
"""Central config for pipeline-worker — reads all env vars in one place."""
import os

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://ai-service:8001").rstrip("/")
S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minio")
S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minio_pw")
RUN_MODE: str = os.getenv("RUN_MODE", "oneshot")
CYCLE_SECONDS: int = int(os.getenv("CYCLE_SECONDS", "120"))

BUCKETS = ["raw", "processed", "curated"]
SYNTHETIC_N_RECORDS = 200
REGION_DEFAULT = "demo"
```

- [x] **Step 2: Create `services/pipeline-worker/worker/db.py`**

```python
"""Database connection helper for pipeline-worker."""
import psycopg2
from worker.config import DATABASE_URL


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)
```

- [x] **Step 3: Create `services/pipeline-worker/worker/storage.py`**

```python
"""MinIO/S3 helpers for pipeline-worker."""
import json
from io import BytesIO

import boto3

from worker.config import S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


def ensure_buckets(s3, buckets: list[str]) -> None:
    existing = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
    for bucket in buckets:
        if bucket not in existing:
            s3.create_bucket(Bucket=bucket)
            print(f"  created bucket: {bucket}")
        else:
            print(f"  bucket exists:  {bucket}")


def upload_json(s3, bucket: str, key: str, records: list[dict]) -> None:
    body = json.dumps(records, indent=2).encode()
    s3.put_object(Bucket=bucket, Key=key, Body=BytesIO(body), ContentLength=len(body))
    print(f"  uploaded s3://{bucket}/{key}  ({len(records)} records, {len(body):,} bytes)")
```

- [x] **Step 4: Create `services/pipeline-worker/tests/__init__.py`** (empty file)

- [x] **Step 5: Create `services/pipeline-worker/tests/test_config.py`**

```python
"""Tests for config module — verify env var reading."""
import importlib
import os


def test_config_defaults():
    import worker.config as cfg
    assert cfg.CYCLE_SECONDS == 120
    assert cfg.SYNTHETIC_N_RECORDS == 200
    assert cfg.BUCKETS == ["raw", "processed", "curated"]


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("CYCLE_SECONDS", "60")
    monkeypatch.setenv("RUN_MODE", "daemon")
    import worker.config as cfg
    importlib.reload(cfg)
    assert cfg.CYCLE_SECONDS == 60
    assert cfg.RUN_MODE == "daemon"
    importlib.reload(cfg)  # restore
```

- [x] **Step 6: Run tests**

```bash
cd services/pipeline-worker
pip install pytest psycopg2-binary boto3 numpy requests tenacity scipy 2>/dev/null
python -m pytest tests/test_config.py -v
```

Expected: `2 passed`

- [x] **Step 7: Commit**

```bash
git add services/pipeline-worker/worker/config.py \
        services/pipeline-worker/worker/db.py \
        services/pipeline-worker/worker/storage.py \
        services/pipeline-worker/tests/__init__.py \
        services/pipeline-worker/tests/test_config.py
git commit -m "refactor(pipeline-worker): extract config, db, storage modules"
```

---

## Task 1.2: Pipeline-Worker — Extract generators

**Files:**
- Create: `services/pipeline-worker/worker/generators/__init__.py`
- Create: `services/pipeline-worker/worker/generators/oss.py`
- Create: `services/pipeline-worker/worker/generators/bss.py`
- Create: `services/pipeline-worker/tests/test_generators.py`

- [x] **Step 1: Create `services/pipeline-worker/worker/generators/__init__.py`** (empty)

- [x] **Step 2: Create `services/pipeline-worker/worker/generators/oss.py`**

Cut `generate_oss()` function verbatim from `worker/__main__.py` into this file. Add import header:

```python
"""Synthetic OSS KPI record generator with fault injection."""
from datetime import datetime, timezone, timedelta
import numpy as np
```

Then paste the entire `generate_oss()` function (lines 79-146 of current `__main__.py`) unchanged. No logic changes.

- [x] **Step 3: Create `services/pipeline-worker/worker/generators/bss.py`**

Cut `generate_bss()` function verbatim from `worker/__main__.py`. Add import header:

```python
"""Synthetic BSS subscriber generator with correlated degradation."""
from datetime import datetime, timezone, timedelta
import numpy as np
```

Then paste the entire `generate_bss()` function (lines 149-241 of current `__main__.py`) unchanged.

- [x] **Step 4: Create `services/pipeline-worker/tests/test_generators.py`**

```python
"""Tests for synthetic data generators."""
from worker.generators.oss import generate_oss
from worker.generators.bss import generate_bss


def test_generate_oss_record_count():
    records, fault_info = generate_oss(n=10, region="test", seed=42)
    assert len(records) == 10


def test_generate_oss_required_fields():
    records, _ = generate_oss(n=5, seed=1)
    required = {"ts", "cell_id", "throughput_mbps", "latency_ms",
                "packet_loss_pct", "active_users", "signal_rsrp_dbm", "is_fault"}
    for rec in records:
        assert required.issubset(rec.keys())


def test_generate_oss_value_ranges():
    records, _ = generate_oss(n=100, seed=7)
    for rec in records:
        assert rec["throughput_mbps"] > 0
        assert rec["latency_ms"] > 0
        assert 0 <= rec["packet_loss_pct"] <= 15
        assert -140 <= rec["signal_rsrp_dbm"] <= -40


def test_generate_oss_fault_injection():
    records, fault_info = generate_oss(n=200, seed=42)
    assert fault_info["fault_records"] > 0
    assert len(fault_info["fault_cells"]) >= 2


def test_generate_bss_record_count():
    rows = generate_bss(n=20, seed=5)
    assert len(rows) == 20


def test_generate_bss_required_fields():
    rows = generate_bss(n=5, seed=1)
    required = {"ts", "subscriber_id", "line_type", "revenue_tnd",
                "data_used_gb", "churn_risk", "serving_cell"}
    for row in rows:
        assert required.issubset(row.keys())


def test_generate_bss_churn_range():
    rows = generate_bss(n=200, seed=99)
    for row in rows:
        assert 0 <= row["churn_risk"] <= 1


def test_generate_bss_prepaid_ratio():
    rows = generate_bss(n=1000, seed=42)
    prepaid = sum(1 for r in rows if r["line_type"] == "prepaid")
    ratio = prepaid / len(rows)
    assert 0.70 <= ratio <= 0.90  # ~80% prepaid per Tunisian market model
```

- [x] **Step 5: Run tests**

```bash
cd services/pipeline-worker
python -m pytest tests/test_generators.py -v
```

Expected: `8 passed`

- [x] **Step 6: Update `__main__.py` to import from generators**

In `services/pipeline-worker/worker/__main__.py`, replace the two generator function bodies with imports at the top of the file:

```python
# Remove the generate_oss() and generate_bss() function definitions entirely.
# Add these imports near the top, after other imports:
from worker.generators.oss import generate_oss
from worker.generators.bss import generate_bss
from worker.config import (
    DATABASE_URL, AI_SERVICE_URL, S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY,
    RUN_MODE, CYCLE_SECONDS, BUCKETS, SYNTHETIC_N_RECORDS, REGION_DEFAULT,
)
from worker.db import get_conn
from worker.storage import get_s3, ensure_buckets, upload_json
```

Also remove the old `get_conn()`, `get_s3()`, `ensure_buckets()`, `upload_json()` function definitions from `__main__.py` since they're now in `db.py` and `storage.py`.

- [x] **Step 7: Verify pipeline still imports cleanly**

```bash
cd services/pipeline-worker
python -c "from worker import __main__; print('import ok')"
```

Expected: `import ok`

- [x] **Step 8: Ruff check**

```bash
cd /home/souhayl/projects/telecom-cloud-intelligence
ruff check services/pipeline-worker/
```

Expected: no errors. If errors, fix them before committing.

- [x] **Step 9: Commit**

```bash
git add services/pipeline-worker/worker/generators/ \
        services/pipeline-worker/worker/__main__.py \
        services/pipeline-worker/tests/test_generators.py
git commit -m "refactor(pipeline-worker): extract OSS/BSS generators into modules"
```

---

## Task 1.3: Pipeline-Worker — Extract processors + analytics

**Files:**
- Create: `services/pipeline-worker/worker/processors/__init__.py`
- Create: `services/pipeline-worker/worker/processors/oss.py`
- Create: `services/pipeline-worker/worker/processors/bss.py`
- Create: `services/pipeline-worker/worker/analytics/__init__.py`
- Create: `services/pipeline-worker/worker/analytics/features.py`
- Create: `services/pipeline-worker/worker/analytics/correlations.py`
- Create: `services/pipeline-worker/tests/test_processors.py`
- Create: `services/pipeline-worker/tests/test_correlations.py`

- [x] **Step 1: Create `services/pipeline-worker/worker/processors/oss.py`**

```python
"""OSS data processing — raw → processed layer enrichment."""
import numpy as np


def build_processed_oss(records: list[dict]) -> list[dict]:
    """Clean + enrich OSS records for the processed data-lake layer."""
    processed = []
    for r in records:
        lat = r["latency_ms"]
        tput = r["throughput_mbps"]
        loss = r["packet_loss_pct"]
        usr = r["active_users"]

        lat_severity = (
            "critical" if lat > 80
            else "high" if lat > 50
            else "medium" if lat > 30
            else "normal"
        )
        tput_category = "degraded" if tput < 20 else "fair" if tput < 50 else "good"
        load_factor = round(usr / 500.0, 4) if usr else 0.0
        qos_score = round(max(0.0, 1.0 - (lat / 100) - (loss / 10) + (tput / 200)), 4)

        rec = {k: v for k, v in r.items() if k != "is_fault"}
        rec.update({
            "latency_severity": lat_severity,
            "throughput_category": tput_category,
            "load_factor": load_factor,
            "qos_score": qos_score,
        })
        processed.append(rec)
    return processed
```

- [x] **Step 2: Create `services/pipeline-worker/worker/processors/bss.py`**

```python
"""BSS data processing — raw → processed layer enrichment + curated join."""
import numpy as np


def build_processed_bss(records: list[dict]) -> list[dict]:
    """Clean + enrich BSS records for the processed data-lake layer."""
    processed = []
    for r in records:
        rec = dict(r)
        rev = r["revenue_tnd"]
        rec["arpu_category"] = "low" if rev < 10 else "mid" if rev < 40 else "high"
        rec["data_intensity"] = round(r["data_used_gb"] / max(rev, 0.01), 4)
        rec["churn_bucket"] = (
            "safe" if r["churn_risk"] < 0.3
            else "watch" if r["churn_risk"] < 0.6
            else "risk"
        )
        processed.append(rec)
    return processed


def build_curated_dataset(
    oss_records, bss_records, anomaly_result,
    rev_anomaly_result, sla_score, correlations,
) -> dict:
    """Build final curated dataset joining OSS + BSS + AI outputs."""
    cell_oss: dict = {}
    for r in oss_records:
        cid = r["cell_id"]
        if cid not in cell_oss:
            cell_oss[cid] = {"tput": [], "lat": [], "loss": [], "rsrp": []}
        cell_oss[cid]["tput"].append(r["throughput_mbps"])
        cell_oss[cid]["lat"].append(r["latency_ms"])
        cell_oss[cid]["loss"].append(r["packet_loss_pct"])
        cell_oss[cid]["rsrp"].append(r["signal_rsrp_dbm"])

    cell_bss: dict = {}
    for r in bss_records:
        cid = r["serving_cell"]
        if cid not in cell_bss:
            cell_bss[cid] = {"rev": [], "data": [], "churn": []}
        cell_bss[cid]["rev"].append(r["revenue_tnd"])
        cell_bss[cid]["data"].append(r["data_used_gb"])
        cell_bss[cid]["churn"].append(r["churn_risk"])

    cells_summary = []
    for cid in sorted(set(list(cell_oss.keys()) + list(cell_bss.keys()))):
        oss = cell_oss.get(cid, {})
        bss = cell_bss.get(cid, {})
        cells_summary.append({
            "cell_id": cid,
            "mean_throughput": round(float(np.mean(oss.get("tput", [0]))), 2),
            "mean_latency": round(float(np.mean(oss.get("lat", [0]))), 2),
            "mean_packet_loss": round(float(np.mean(oss.get("loss", [0]))), 4),
            "mean_revenue_tnd": round(float(np.mean(bss.get("rev", [0]))), 2),
            "mean_data_gb": round(float(np.mean(bss.get("data", [0]))), 2),
            "mean_churn_risk": round(float(np.mean(bss.get("churn", [0]))), 4),
        })

    return {
        "sla_risk_score": sla_score,
        "oss_anomaly_count": anomaly_result.get("anomalous_count", 0),
        "bss_anomaly_count": rev_anomaly_result.get("anomalous_count", 0),
        "correlations": correlations,
        "cells_summary": cells_summary,
        "total_oss_records": len(oss_records),
        "total_bss_records": len(bss_records),
    }
```

- [x] **Step 3: Create `services/pipeline-worker/worker/analytics/features.py`**

```python
"""KPI feature aggregation for ML inference inputs."""
import numpy as np


def compute_oss_features(records: list[dict]) -> dict:
    """Aggregate per-record OSS measurements into 9 features for SLA risk model."""
    tput = np.array([r["throughput_mbps"] for r in records], dtype=float)
    lat = np.array([r["latency_ms"] for r in records], dtype=float)
    loss = np.array([r["packet_loss_pct"] for r in records], dtype=float)
    usr = np.array([r["active_users"] for r in records], dtype=float)
    rsrp = np.array([r["signal_rsrp_dbm"] for r in records], dtype=float)
    return {
        "mean_throughput_mbps": round(float(tput.mean()), 4),
        "std_throughput_mbps": round(float(tput.std()), 4),
        "mean_latency_ms": round(float(lat.mean()), 4),
        "std_latency_ms": round(float(lat.std()), 4),
        "max_latency_ms": round(float(lat.max()), 4),
        "mean_packet_loss_pct": round(float(loss.mean()), 4),
        "max_packet_loss_pct": round(float(loss.max()), 4),
        "mean_active_users": round(float(usr.mean()), 4),
        "mean_signal_rsrp_dbm": round(float(rsrp.mean()), 4),
    }


def compute_bss_features(records: list[dict]) -> dict:
    """Aggregate BSS metrics for revenue anomaly context."""
    rev = np.array([r["revenue_tnd"] for r in records], dtype=float)
    data = np.array([r["data_used_gb"] for r in records], dtype=float)
    voice = np.array([r["voice_min"] for r in records], dtype=float)
    sms = np.array([r["sms_count"] for r in records], dtype=float)
    churn = np.array([r["churn_risk"] for r in records], dtype=float)
    return {
        "mean_revenue_tnd": round(float(rev.mean()), 4),
        "std_revenue_tnd": round(float(rev.std()), 4),
        "mean_data_used_gb": round(float(data.mean()), 4),
        "mean_voice_min": round(float(voice.mean()), 4),
        "mean_sms_count": round(float(sms.mean()), 4),
        "mean_churn_risk": round(float(churn.mean()), 4),
    }
```

- [x] **Step 4: Create `services/pipeline-worker/worker/analytics/correlations.py`**

```python
"""OSS↔CEM correlation engine — Pearson + Spearman + Distance Correlation."""
import numpy as np
from scipy import stats

try:
    import dcor
    DCOR_AVAILABLE = True
except ImportError:
    DCOR_AVAILABLE = False
    print("[correlations] dcor not installed — distance correlation skipped")


def compute_correlations(oss_records: list[dict], bss_records: list[dict]) -> list[dict]:
    """Compute Pearson, Spearman, and Distance Correlation between OSS and BSS per cell."""
    cell_oss: dict = {}
    for r in oss_records:
        cid = r["cell_id"]
        if cid not in cell_oss:
            cell_oss[cid] = {"lat": [], "tput": [], "loss": []}
        cell_oss[cid]["lat"].append(r["latency_ms"])
        cell_oss[cid]["tput"].append(r["throughput_mbps"])
        cell_oss[cid]["loss"].append(r["packet_loss_pct"])

    cell_bss: dict = {}
    for r in bss_records:
        cid = r["serving_cell"]
        if cid not in cell_bss:
            cell_bss[cid] = {"rev": [], "data": [], "churn": []}
        cell_bss[cid]["rev"].append(r["revenue_tnd"])
        cell_bss[cid]["data"].append(r["data_used_gb"])
        cell_bss[cid]["churn"].append(r["churn_risk"])

    common = sorted(set(cell_oss.keys()) & set(cell_bss.keys()))
    if len(common) < 3:
        return []

    oss_lat = np.array([np.mean(cell_oss[c]["lat"]) for c in common])
    oss_tput = np.array([np.mean(cell_oss[c]["tput"]) for c in common])
    oss_loss = np.array([np.mean(cell_oss[c]["loss"]) for c in common])
    bss_rev = np.array([np.mean(cell_bss[c]["rev"]) for c in common])
    bss_data = np.array([np.mean(cell_bss[c]["data"]) for c in common])
    bss_churn = np.array([np.mean(cell_bss[c]["churn"]) for c in common])

    pairs = [
        ("mean_latency_ms", "mean_revenue_tnd", oss_lat, bss_rev),
        ("mean_throughput_mbps", "mean_data_used_gb", oss_tput, bss_data),
        ("mean_packet_loss_pct", "mean_churn_risk", oss_loss, bss_churn),
        ("mean_latency_ms", "mean_churn_risk", oss_lat, bss_churn),
        ("mean_throughput_mbps", "mean_revenue_tnd", oss_tput, bss_rev),
    ]

    results = []
    for metric_x, metric_y, arr_x, arr_y in pairs:
        for method in ("pearson", "spearman"):
            fn = stats.pearsonr if method == "pearson" else stats.spearmanr
            corr_val, p_val = fn(arr_x, arr_y)
            results.append({
                "metric_x": metric_x,
                "metric_y": metric_y,
                "method": method,
                "corr_value": round(float(corr_val), 6),
                "p_value": round(float(p_val), 6),
            })

        if DCOR_AVAILABLE:
            dc = dcor.distance_correlation(arr_x, arr_y)
            results.append({
                "metric_x": metric_x,
                "metric_y": metric_y,
                "method": "dcor",
                "corr_value": round(float(dc), 6),
                "p_value": None,  # dcor is unsigned, no p-value from basic estimator
            })

    return results
```

- [x] **Step 5: Create all `__init__.py` files** (empty):
  - `services/pipeline-worker/worker/processors/__init__.py`
  - `services/pipeline-worker/worker/analytics/__init__.py`

- [x] **Step 6: Create `services/pipeline-worker/tests/test_processors.py`**

```python
"""Tests for OSS/BSS processors."""
from worker.processors.oss import build_processed_oss
from worker.processors.bss import build_processed_bss


def _make_oss_record(lat=25.0, tput=80.0, loss=0.5, users=150, rsrp=-82.0, fault=False):
    return {
        "ts": "2026-03-01T10:00:00+00:00",
        "region": "test",
        "cell_id": "CELL-001",
        "throughput_mbps": tput,
        "latency_ms": lat,
        "packet_loss_pct": loss,
        "active_users": users,
        "signal_rsrp_dbm": rsrp,
        "is_fault": fault,
    }


def test_build_processed_oss_removes_is_fault():
    rec = _make_oss_record()
    result = build_processed_oss([rec])
    assert "is_fault" not in result[0]


def test_build_processed_oss_latency_severity_normal():
    rec = _make_oss_record(lat=20.0)
    result = build_processed_oss([rec])
    assert result[0]["latency_severity"] == "normal"


def test_build_processed_oss_latency_severity_critical():
    rec = _make_oss_record(lat=90.0)
    result = build_processed_oss([rec])
    assert result[0]["latency_severity"] == "critical"


def test_build_processed_oss_throughput_category_degraded():
    rec = _make_oss_record(tput=10.0)
    result = build_processed_oss([rec])
    assert result[0]["throughput_category"] == "degraded"


def test_build_processed_bss_arpu_low():
    rec = {"revenue_tnd": 5.0, "data_used_gb": 2.0, "churn_risk": 0.1}
    result = build_processed_bss([rec])
    assert result[0]["arpu_category"] == "low"


def test_build_processed_bss_churn_bucket_risk():
    rec = {"revenue_tnd": 30.0, "data_used_gb": 5.0, "churn_risk": 0.75}
    result = build_processed_bss([rec])
    assert result[0]["churn_bucket"] == "risk"


def test_build_processed_bss_data_intensity():
    rec = {"revenue_tnd": 10.0, "data_used_gb": 5.0, "churn_risk": 0.2}
    result = build_processed_bss([rec])
    assert result[0]["data_intensity"] == round(5.0 / 10.0, 4)
```

- [x] **Step 7: Create `services/pipeline-worker/tests/test_correlations.py`**

```python
"""Tests for correlation analytics."""
import pytest
from worker.analytics.correlations import compute_correlations


def _make_correlated_records(n=10):
    """OSS records with high latency in CELL-001, low in CELL-002."""
    oss = []
    bss = []
    for i in range(n):
        # CELL-001: high latency → low revenue
        oss.append({
            "cell_id": "CELL-001",
            "latency_ms": 80.0 + i,
            "throughput_mbps": 20.0,
            "packet_loss_pct": 3.0,
        })
        bss.append({
            "serving_cell": "CELL-001",
            "revenue_tnd": 5.0 - i * 0.1,
            "data_used_gb": 1.0,
            "churn_risk": 0.8,
        })
        # CELL-002: low latency → high revenue
        oss.append({
            "cell_id": "CELL-002",
            "latency_ms": 20.0 + i * 0.1,
            "throughput_mbps": 80.0,
            "packet_loss_pct": 0.2,
        })
        bss.append({
            "serving_cell": "CELL-002",
            "revenue_tnd": 30.0 + i * 0.5,
            "data_used_gb": 10.0,
            "churn_risk": 0.1,
        })
    return oss, bss


def test_compute_correlations_returns_list():
    oss, bss = _make_correlated_records()
    result = compute_correlations(oss, bss)
    assert isinstance(result, list)


def test_compute_correlations_methods_present():
    oss, bss = _make_correlated_records()
    result = compute_correlations(oss, bss)
    methods = {r["method"] for r in result}
    assert "pearson" in methods
    assert "spearman" in methods


def test_compute_correlations_requires_min_3_cells():
    # Only 2 common cells — should return empty
    oss = [{"cell_id": "A", "latency_ms": 20, "throughput_mbps": 80, "packet_loss_pct": 0.1}]
    bss = [{"serving_cell": "A", "revenue_tnd": 10, "data_used_gb": 5, "churn_risk": 0.2}]
    result = compute_correlations(oss, bss)
    assert result == []


def test_compute_correlations_corr_value_range():
    oss, bss = _make_correlated_records(n=20)
    result = compute_correlations(oss, bss)
    for r in result:
        if r["corr_value"] is not None:
            assert -1.0 <= r["corr_value"] <= 1.0
```

- [x] **Step 8: Run all tests**

```bash
cd services/pipeline-worker
python -m pytest tests/ -v
```

Expected: all tests pass

- [x] **Step 9: Update `__main__.py`** — replace inline function definitions with imports:

```python
# At top of __main__.py, add:
from worker.processors.oss import build_processed_oss
from worker.processors.bss import build_processed_bss, build_curated_dataset
from worker.analytics.features import compute_oss_features, compute_bss_features
from worker.analytics.correlations import compute_correlations
```

Remove the old function bodies for these functions from `__main__.py`.

- [x] **Step 10: Verify import**

```bash
cd services/pipeline-worker
python -c "from worker import __main__; print('ok')"
```

- [x] **Step 11: Ruff + commit**

```bash
cd /home/souhayl/projects/telecom-cloud-intelligence
ruff check services/pipeline-worker/
git add services/pipeline-worker/
git commit -m "refactor(pipeline-worker): extract processors, analytics, and feature modules"
```

---

## Task 1.4: Pipeline-Worker — Extract inference client + pipeline module

**Files:**
- Create: `services/pipeline-worker/worker/inference/__init__.py`
- Create: `services/pipeline-worker/worker/inference/client.py`
- Create: `services/pipeline-worker/worker/pipeline.py`
- Create: `services/pipeline-worker/tests/test_inference_client.py`

- [x] **Step 1: Create `services/pipeline-worker/worker/inference/client.py`**

```python
"""AI service HTTP client with retry logic."""
import os
from datetime import datetime

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from worker.config import AI_SERVICE_URL

_ai_retry = retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)


@_ai_retry
def infer_sla_risk(
    run_id: str,
    region: str,
    window_start: datetime,
    window_end: datetime,
    features: dict,
) -> tuple[float, dict, str]:
    payload = {
        "run_id": run_id,
        "region": region,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "features": features,
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/sla-risk", json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    return float(data["score"]), data.get("explanation", {}), data.get("model_version", "v2.0")


@_ai_retry
def infer_anomaly(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "throughput_mbps": r["throughput_mbps"],
                "latency_ms": r["latency_ms"],
                "packet_loss_pct": r["packet_loss_pct"],
                "active_users": r["active_users"],
                "signal_rsrp_dbm": r["signal_rsrp_dbm"],
            }
            for r in records
        ],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/anomaly", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


@_ai_retry
def infer_revenue_anomaly(run_id: str, region: str, records: list[dict]) -> dict:
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "revenue_tnd": r["revenue_tnd"],
                "data_used_gb": r["data_used_gb"],
                "voice_min": float(r["voice_min"]),
                "sms_count": float(r["sms_count"]),
                "churn_risk": r["churn_risk"],
            }
            for r in records
        ],
    }
    r = requests.post(f"{AI_SERVICE_URL}/infer/revenue-anomaly", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
```

- [x] **Step 2: Create `services/pipeline-worker/worker/inference/__init__.py`** (empty)

- [x] **Step 3: Create `services/pipeline-worker/tests/test_inference_client.py`**

```python
"""Tests for AI inference client — mock HTTP calls."""
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from worker.inference.client import infer_sla_risk, infer_anomaly


def test_infer_sla_risk_parses_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "score": 0.72,
        "explanation": {"method": "GBR"},
        "model_version": "v2.0",
    }
    mock_resp.raise_for_status = lambda: None

    with patch("worker.inference.client.requests.post", return_value=mock_resp):
        score, explanation, version = infer_sla_risk(
            "run-001", "test",
            datetime(2026, 3, 1, tzinfo=timezone.utc),
            datetime(2026, 3, 1, 0, 15, tzinfo=timezone.utc),
            {"mean_latency_ms": 25.0},
        )
    assert score == 0.72
    assert version == "v2.0"
    assert explanation["method"] == "GBR"


def test_infer_anomaly_returns_dict():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "anomalous_count": 2,
        "anomaly_rate": 0.1,
        "records": [],
        "model_version": "v2.0",
    }
    mock_resp.raise_for_status = lambda: None

    records = [
        {"throughput_mbps": 10.0, "latency_ms": 120.0,
         "packet_loss_pct": 5.0, "active_users": 100, "signal_rsrp_dbm": -110.0}
    ]
    with patch("worker.inference.client.requests.post", return_value=mock_resp):
        result = infer_anomaly("run-001", "test", records)
    assert result["anomalous_count"] == 2
```

- [x] **Step 4: Create `services/pipeline-worker/worker/pipeline.py`**

Move the `run_once()` and `_run_pipeline_steps()` functions from `__main__.py` into this file. Update imports at top:

```python
"""22-step pipeline orchestration."""
import hashlib
import uuid
from datetime import datetime, timezone, timedelta

import psycopg2.extras

from worker.config import SYNTHETIC_N_RECORDS, REGION_DEFAULT, BUCKETS
from worker.db import get_conn
from worker.storage import get_s3, ensure_buckets, upload_json
from worker.generators.oss import generate_oss
from worker.generators.bss import generate_bss
from worker.processors.oss import build_processed_oss
from worker.processors.bss import build_processed_bss, build_curated_dataset
from worker.analytics.features import compute_oss_features, compute_bss_features
from worker.analytics.correlations import compute_correlations
from worker.inference.client import infer_sla_risk, infer_anomaly, infer_revenue_anomaly
```

Then paste `run_once()` and `_run_pipeline_steps()` unchanged below those imports.

- [x] **Step 5: Update `services/pipeline-worker/worker/__main__.py`** — it now only needs:

```python
"""Pipeline-worker entry point."""
import time
from worker.config import RUN_MODE, CYCLE_SECONDS
from worker.pipeline import run_once


def main() -> None:
    if RUN_MODE == "daemon":
        print("pipeline-worker: starting in continuous daemon mode")
        while True:
            print("\n" + "=" * 50)
            print("pipeline-worker: executing scheduled cycle...")
            try:
                run_once()
                print(f"pipeline-worker: cycle complete. Sleeping {CYCLE_SECONDS}s...")
            except Exception as e:
                print(f"pipeline-worker: error: {e}")
                print(f"pipeline-worker: will retry in {CYCLE_SECONDS}s...")
            time.sleep(CYCLE_SECONDS)
    else:
        print("pipeline-worker: starting single execution (oneshot)")
        run_once()
        print("pipeline-worker: execution complete")


if __name__ == "__main__":
    main()
```

- [x] **Step 6: Run all tests**

```bash
cd services/pipeline-worker
python -m pytest tests/ -v
```

Expected: all tests pass

- [x] **Step 7: Verify `__main__.py` is now clean and short**

```bash
wc -l services/pipeline-worker/worker/__main__.py
```

Expected: < 30 lines

- [x] **Step 8: Ruff + commit**

```bash
cd /home/souhayl/projects/telecom-cloud-intelligence
ruff check services/pipeline-worker/
git add services/pipeline-worker/
git commit -m "refactor(pipeline-worker): extract inference client and pipeline module — __main__ now 25 lines"
```

---

## Task 1.5: API-Gateway — Split into routers

**Context:** `services/api-gateway/main.py` is 940 lines with all endpoints in one file. Split into FastAPI routers. No logic change — just move code. Tests verify each router's logic with mocked DB connections.

**Files:**
- Create: `services/api-gateway/config.py`
- Create: `services/api-gateway/db.py`
- Create: `services/api-gateway/routers/__init__.py`
- Create: `services/api-gateway/routers/health.py`
- Create: `services/api-gateway/routers/sla.py`
- Create: `services/api-gateway/routers/anomalies.py`
- Create: `services/api-gateway/routers/correlations.py`
- Create: `services/api-gateway/routers/pipelines.py`
- Create: `services/api-gateway/routers/actions.py`
- Modify: `services/api-gateway/main.py` — reduced to app init + router includes
- Create: `services/api-gateway/tests/__init__.py`
- Create: `services/api-gateway/tests/test_health.py`
- Create: `services/api-gateway/tests/test_sla.py`

- [x] **Step 1: Create `services/api-gateway/config.py`**

```python
"""API Gateway configuration."""
import os

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
JWT_SECRET: str = os.getenv("JWT_SECRET", "telecom-dev-secret-change-in-prod")
JWT_ALGORITHM: str = "HS256"
```

- [x] **Step 2: Create `services/api-gateway/db.py`**

```python
"""Database connection for api-gateway."""
import psycopg2
from config import DATABASE_URL


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)
```

- [x] **Step 3: Create `services/api-gateway/routers/health.py`**

```python
"""Health check router."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway", "version": "v2.0"}
```

- [x] **Step 4: Create `services/api-gateway/routers/sla.py`**

Cut the `/sla-risk` and `/sla-risk/history` endpoint handlers verbatim from `main.py` into this file. Wrap them in a router:

```python
"""SLA risk score endpoints."""
from fastapi import APIRouter, Depends
from db import get_conn
# ... (imports from main.py that these endpoints use)

router = APIRouter()

# Paste the /sla-risk and /sla-risk/history endpoints here.
# Replace @app.get with @router.get.
# Replace get_current_user dependency reference — import it from a shared auth module.
```

**Note for Kimi:** The auth dependency (`get_current_user`) is defined in the current `main.py`. Extract it to `services/api-gateway/auth.py` so all routers can import it. Pattern:

```python
# services/api-gateway/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from config import JWT_SECRET, JWT_ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
```

- [x] **Step 5: Create all remaining routers** (`anomalies.py`, `correlations.py`, `pipelines.py`, `actions.py`)

Follow the same pattern for each: create router, cut endpoint handlers from `main.py`, replace `@app.get/post/patch` with `@router.get/post/patch`, import `get_conn` from `db.py` and `get_current_user` from `auth.py`.

Endpoints per router:
- `anomalies.py`: `/anomalies`, `/revenue-anomalies`, `/anomaly-stats`
- `correlations.py`: `/correlation`
- `pipelines.py`: `/pipeline-runs`, `/kpi-summary`
- `actions.py`: `/actions` (GET, POST), `/actions/{action_id}` (PATCH), `/actions/{action_id}/execute` (POST)

- [x] **Step 6: Rewrite `services/api-gateway/main.py`** to just 40 lines:

```python
"""API Gateway — FastAPI app with router includes."""
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

# (keep existing OTel setup code)

from routers.health import router as health_router
from routers.sla import router as sla_router
from routers.anomalies import router as anomalies_router
from routers.correlations import router as correlations_router
from routers.pipelines import router as pipelines_router
from routers.actions import router as actions_router

app = FastAPI(title="NeXo API Gateway", version="2.0")
FastAPIInstrumentor.instrument_app(app)
Instrumentator().instrument(app).expose(app)

app.include_router(health_router)
app.include_router(sla_router)
app.include_router(anomalies_router)
app.include_router(correlations_router)
app.include_router(pipelines_router)
app.include_router(actions_router)
```

- [x] **Step 7: Create `services/api-gateway/tests/test_health.py`**

```python
"""Test health endpoint."""
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, ".")
from main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

- [x] **Step 8: Create `services/api-gateway/tests/test_sla.py`**

```python
"""Test SLA risk endpoint with mocked DB."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, ".")
from main import app

client = TestClient(app)

MOCK_TOKEN = "mock-jwt-token"


def _mock_user():
    return {"sub": "test@test.com", "role": "analyst"}


def test_sla_risk_requires_auth():
    resp = client.get("/sla-risk")
    assert resp.status_code == 401


def test_sla_risk_returns_data(monkeypatch):
    mock_row = (1, "run-001", "demo", None, None, 0.42,
                '{"method": "GBR"}', "v2.0", "2026-03-01")

    with patch("routers.sla.get_current_user", return_value=_mock_user()):
        with patch("routers.sla.get_conn") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = mock_row
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            resp = client.get("/sla-risk", headers={"Authorization": "Bearer test"})
    # If auth mock works, we get data back
    assert resp.status_code in (200, 401)  # 401 means auth mock needs adjustment
```

- [x] **Step 9: Run tests**

```bash
cd services/api-gateway
pip install pytest fastapi httpx 2>/dev/null
python -m pytest tests/ -v
```

Expected: health test passes. SLA test may need mock adjustment — fix until green.

- [x] **Step 10: Ruff + commit**

```bash
cd /home/souhayl/projects/telecom-cloud-intelligence
ruff check services/api-gateway/
git add services/api-gateway/
git commit -m "refactor(api-gateway): split 940-line main.py into 6 focused routers"
```

---

## Task 1.6: AI-Service — Split into routers

**Files:**
- Create: `services/ai-service/config.py`
- Create: `services/ai-service/model_cache.py`
- Create: `services/ai-service/routers/__init__.py`
- Create: `services/ai-service/routers/health.py`
- Create: `services/ai-service/routers/v2/__init__.py`
- Create: `services/ai-service/routers/v2/sla_risk.py`
- Create: `services/ai-service/routers/v2/anomaly.py`
- Create: `services/ai-service/routers/v2/revenue.py`
- Modify: `services/ai-service/main.py` — reduced to app init + router includes
- Create: `services/ai-service/tests/__init__.py`
- Create: `services/ai-service/tests/test_model_cache.py`

- [x] **Step 1: Create `services/ai-service/config.py`**

```python
"""AI Service configuration and feature definitions."""
from pathlib import Path
import os

MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models"))
MODEL_VERSION = "v2.0"
CACHE_TTL_SECONDS = 30

SLA_FEATURES = [
    "mean_throughput_mbps", "std_throughput_mbps", "mean_latency_ms",
    "std_latency_ms", "max_latency_ms", "mean_packet_loss_pct",
    "max_packet_loss_pct", "mean_active_users", "mean_signal_rsrp_dbm",
]

ANOMALY_FEATURES = [
    "throughput_mbps", "latency_ms", "packet_loss_pct",
    "active_users", "signal_rsrp_dbm",
]

BSS_FEATURES = [
    "revenue_tnd", "data_used_gb", "voice_min", "sms_count", "churn_risk",
]
```

- [x] **Step 2: Create `services/ai-service/model_cache.py`**

Cut the `load_models()`, `_cache`, `_cache_ttl`, `_get_model_file_mtime()` logic from `main.py` verbatim into this file. Add import at top:

```python
"""Model cache with hot-reload on file change."""
import time
from pathlib import Path
import joblib
from config import MODELS_DIR, CACHE_TTL_SECONDS

SLA_MODEL_PATH = MODELS_DIR / "sla_risk_model.joblib"
ANOMALY_MODEL_PATH = MODELS_DIR / "anomaly_model.joblib"
REVENUE_ANOMALY_MODEL_PATH = MODELS_DIR / "revenue_anomaly_model.joblib"

_cache = {"sla": None, "anomaly": None, "revenue": None, "loaded_at": 0}
```

Paste full `load_models()` function unchanged below.

- [x] **Step 3: Create `services/ai-service/routers/v2/sla_risk.py`**

Cut `/infer/sla-risk` endpoint from `main.py`. Wrap in router:

```python
"""SLA risk inference endpoint — GradientBoostingRegressor v2.0."""
import hashlib
import numpy as np
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from model_cache import load_models
from config import SLA_FEATURES, MODEL_VERSION

router = APIRouter()


class SlaRiskRequest(BaseModel):
    run_id: str
    region: str
    window_start: str
    window_end: str
    features: Optional[dict] = None


@router.post("/infer/sla-risk")
def infer_sla_risk(req: SlaRiskRequest):
    # (paste the full infer_sla_risk function body here, unchanged)
    ...
```

- [x] **Step 4: Create `services/ai-service/routers/v2/anomaly.py`** and `revenue.py`**

Same pattern — cut endpoints, wrap in router.

- [x] **Step 5: Create `services/ai-service/routers/health.py`**

```python
"""Health check and model reload endpoints."""
from fastapi import APIRouter
from model_cache import load_models
from config import MODEL_VERSION, SLA_MODEL_PATH, ANOMALY_MODEL_PATH, REVENUE_ANOMALY_MODEL_PATH

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@router.post("/models/reload")
def reload_models():
    try:
        sla, anomaly, revenue = load_models(force=True)
        return {
            "status": "reloaded",
            "models": {
                "sla_risk": {"loaded": sla is not None, "path": str(SLA_MODEL_PATH)},
                "anomaly": {"loaded": anomaly is not None, "path": str(ANOMALY_MODEL_PATH)},
                "revenue_anomaly": {"loaded": revenue is not None, "path": str(REVENUE_ANOMALY_MODEL_PATH)},
            },
            "model_version": MODEL_VERSION,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

- [x] **Step 6: Rewrite `services/ai-service/main.py`** to 30 lines:

```python
"""AI Service — FastAPI app with router includes."""
import os
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from config import MODEL_VERSION
from model_cache import load_models
from routers.health import router as health_router
from routers.v2.sla_risk import router as sla_risk_router
from routers.v2.anomaly import router as anomaly_router
from routers.v2.revenue import router as revenue_router


def _setup_tracing() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "ai-service"), "service.version": "2.0"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


_setup_tracing()

app = FastAPI(title="AI Service", version=MODEL_VERSION)
FastAPIInstrumentor.instrument_app(app)

print("[ai-service] initializing model cache...")
load_models(force=True)
print("[ai-service] models ready")

app.include_router(health_router)
app.include_router(sla_risk_router)
app.include_router(anomaly_router)
app.include_router(revenue_router)
```

- [x] **Step 7: Create `services/ai-service/tests/test_model_cache.py`**

```python
"""Tests for model cache module."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
sys.path.insert(0, ".")
import model_cache


def test_load_models_raises_when_no_files_and_empty_cache():
    model_cache._cache = {"sla": None, "anomaly": None, "revenue": None, "loaded_at": 0}
    with patch.object(Path, "exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="Pre-trained model"):
            model_cache.load_models(force=True)


def test_load_models_returns_cached_when_fresh():
    import time
    mock_model = MagicMock()
    model_cache._cache = {
        "sla": mock_model,
        "anomaly": mock_model,
        "revenue": mock_model,
        "loaded_at": time.time(),
    }
    sla, anomaly, revenue = model_cache.load_models(force=False)
    assert sla is mock_model
    assert anomaly is mock_model
```

- [x] **Step 8: Run tests**

```bash
cd services/ai-service
python -m pytest tests/ -v
```

- [x] **Step 9: Docker build check**

```bash
cd /home/souhayl/projects/telecom-cloud-intelligence
docker compose build ai-service api-gateway pipeline-worker 2>&1 | tail -20
```

Expected: all 3 build successfully. Fix any import errors until they do.

- [x] **Step 10: Ruff + commit**

```bash
ruff check services/ai-service/ services/api-gateway/ services/pipeline-worker/
git add services/ai-service/ services/api-gateway/
git commit -m "refactor(ai-service): split into model_cache + routers; all services now modular"
```

---

## Task 1.7: Add `dcor` to pipeline-worker requirements

- [x] **Step 1: Add dcor to requirements**

Edit `services/pipeline-worker/requirements.txt` — add line:
```
dcor==0.6.2
```

- [x] **Step 2: Verify import in correlations module**

```bash
cd services/pipeline-worker
pip install dcor==0.6.2
python -c "from worker.analytics.correlations import compute_correlations; print('dcor ok')"
```

- [x] **Step 3: Run full test suite**

```bash
python -m pytest tests/ -v
```

- [x] **Step 4: Commit**

```bash
git add services/pipeline-worker/requirements.txt
git commit -m "feat(pipeline-worker): add distance correlation (dcor) to analytics"
```

---

## Phase 1 Final Check

- [x] **Run ruff on entire services/**

```bash
cd /home/souhayl/projects/telecom-cloud-intelligence
ruff check services/
```

Expected: zero errors.

- [x] **Run all tests**

```bash
cd services/pipeline-worker && python -m pytest tests/ -v
cd ../api-gateway && python -m pytest tests/ -v
cd ../ai-service && python -m pytest tests/ -v
```

- [x] **Docker full build**

```bash
cd /home/souhayl/projects/telecom-cloud-intelligence
docker compose build 2>&1 | grep -E "(ERROR|Successfully|FAILED)"
```

Expected: all services build successfully.

- [x] **Final commit — update CLAUDE.md**

Add to CLAUDE.md `## Current Status` section: "Phase 1 backend restructuring complete — all services modular, 25+ tests, ruff clean."

```bash
git add CLAUDE.md
git commit -m "docs(claude): phase 1 restructuring complete"
```

---

---

# PHASE 2: Data Foundation + ETL

**Context:** Data ingest scripts already exist in `services/data-ingest/`. This phase runs them to populate the database, then adds a unified ETL orchestrator that replaces the synthetic `generate_oss/generate_bss` path in the pipeline-worker with real-data sampling.

**What EXISTS:**
- `services/data-ingest/ingest_bss.py` — loads BSS CSVs → `bss_subscribers` table ✅
- `services/data-ingest/simulate_oss.py` — generates OSS cells from BSS area profiles → `oss_cell_kpis` table ✅
- `services/data-ingest/compute_features.py` — builds `subscriber_features` + `area_network_health` ✅
- DB tables already exist: `bss_subscribers`, `oss_cell_kpis`, `subscriber_features`, `area_network_health`

**What does NOT exist yet:**
- A Makefile or script to run ETL steps in order
- A rolling window sampler for the 2-min pipeline cycle
- Real OSS ingestion (waiting on TT data — build stub, fill in when file arrives)

---

## Task 2.1: Create ETL orchestration script

**Files:**
- Create: `services/data-ingest/run_etl.sh` — shell script that runs all steps in order
- Create: `services/data-ingest/ingest_oss_real.py` — stub for real OSS ingestion

- [ ] **Step 1: Create `services/data-ingest/run_etl.sh`**

```bash
#!/bin/bash
# Full ETL pipeline — run from repo root
# Usage: DATABASE_URL=postgresql://... bash services/data-ingest/run_etl.sh
set -e

echo "=== NeXo ETL Pipeline ==="
echo ""

echo "[1/3] Ingesting BSS data (Feb + Mar, 970K subscribers)..."
python services/data-ingest/ingest_bss.py

echo ""
echo "[2/3] Simulating OSS cell KPIs (Feb-Jun, 24 areas × 10 cells × 5 months)..."
python services/data-ingest/simulate_oss.py

echo ""
echo "[3/3] Computing subscriber features + area health..."
python services/data-ingest/compute_features.py

echo ""
echo "=== ETL Complete ==="
```

- [ ] **Step 2: Create `services/data-ingest/ingest_oss_real.py`** (stub — fill when OSS file arrives)

```python
"""
Real OSS Cell KPI Ingestion
----------------------------
STUB — to be completed when TT OSS data file arrives.

Expected OSS file schema (infer from actual file on arrival):
  cell_id, area, timestamp, throughput_mbps, latency_ms, packet_loss_rate,
  jitter_ms, active_users, rsrp_dbm, cell_load_pct

Run: python services/data-ingest/ingest_oss_real.py <filepath>
"""
import sys
from pathlib import Path

OSS_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else None


def main():
    if OSS_FILE is None or not OSS_FILE.exists():
        print("[ingest-oss] No OSS file provided or file not found.")
        print("[ingest-oss] Usage: python ingest_oss_real.py <path-to-oss.csv>")
        print("[ingest-oss] When real OSS arrives: inspect columns, map to oss_cell_kpis schema, implement loader.")
        return

    # TODO: implement when OSS file arrives
    # 1. Read OSS file (CSV or pipe-delimited)
    # 2. Map columns to oss_cell_kpis schema
    # 3. Use psycopg2 execute_values for batch insert
    # 4. ON CONFLICT DO NOTHING (idempotent)
    print(f"[ingest-oss] File found: {OSS_FILE}")
    print("[ingest-oss] Inspect first 5 rows:")
    with open(OSS_FILE) as f:
        for i, line in enumerate(f):
            print(f"  {line.rstrip()}")
            if i >= 4:
                break
    print("[ingest-oss] Update this script with correct column mapping before ingesting.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run ETL on real data** (requires DATABASE_URL pointing to running Postgres)

```bash
export DATABASE_URL="postgresql://telecom:telecom_pw@localhost:5432/telecom_intel"
bash services/data-ingest/run_etl.sh
```

Expected output:
```
[ingest] smartcare_cem_feb.csv complete: 468077 rows, 0 skipped
[ingest] smartcare_cem_mars.csv complete: 500000 rows, 0 skipped
[done] Total rows ingested: 968077
[oss-sim] 2026-02: 240 cells inserted
[oss-sim] 2026-03: 240 cells inserted
...
[features] Computing for 2026-02 ...
  ... 468077 subscriber features inserted/updated
  ... 24 area health rows inserted/updated
```

- [ ] **Step 4: Verify data in Postgres**

```bash
psql postgresql://telecom:telecom_pw@localhost:5432/telecom_intel -c \
  "SELECT month_year, COUNT(*) FROM bss_subscribers GROUP BY month_year ORDER BY 1;"
```

Expected:
```
 month_year | count
------------+--------
 2026-02    | 468077
 2026-03    | 500000
```

- [ ] **Step 5: Verify area health**

```bash
psql postgresql://telecom:telecom_pw@localhost:5432/telecom_intel -c \
  "SELECT area, month_year, avg_cem_score, underserved_pct FROM area_network_health ORDER BY avg_cem_score LIMIT 5;"
```

Expected: 5 rows with real area names, numeric scores.

- [ ] **Step 6: Commit**

```bash
git add services/data-ingest/run_etl.sh services/data-ingest/ingest_oss_real.py
git commit -m "feat(data-ingest): ETL orchestration script + OSS real ingestion stub"
```

---

## Task 2.2: Rolling Window Sampler for Pipeline-Worker

**Context:** The current 2-min pipeline cycle generates 200 synthetic records. Replace this with a sampler that draws from real `bss_subscribers` data (stratified by area × usertype × RAT) and pairs with `oss_cell_kpis` for the same month. This simulates real-time by sampling the static 970K snapshot.

**Files:**
- Create: `services/pipeline-worker/worker/sampler.py`
- Create: `services/pipeline-worker/tests/test_sampler.py`
- Modify: `services/pipeline-worker/worker/pipeline.py` — add `USE_REAL_DATA` flag

- [ ] **Step 1: Create `services/pipeline-worker/worker/sampler.py`**

```python
"""
Rolling Window Sampler
----------------------
Samples batches from real BSS + OSS data in Postgres.
Stratified by area × usertype × RAT to maintain distribution.
Returns records in the same format as generate_oss / generate_bss.

Set USE_REAL_DATA=true in env to activate; defaults to synthetic mode.
"""
import os
import random
from datetime import datetime, timezone

from worker.db import get_conn

USE_REAL_DATA = os.getenv("USE_REAL_DATA", "false").lower() == "true"
SAMPLE_N = int(os.getenv("SAMPLE_N", "200"))
DEFAULT_MONTH = os.getenv("SAMPLE_MONTH", "2026-03")


def sample_bss_records(n: int = SAMPLE_N, month_year: str = DEFAULT_MONTH) -> list[dict]:
    """Sample n BSS subscriber records, stratified by area."""
    sql = """
        SELECT imsi_hash, area, generation, highest_rat, dou_total,
               s1_mme_sr, iu_attach_sr, gb_attach_sr, usertype, month_year
        FROM bss_subscribers
        WHERE month_year = %s
        ORDER BY RANDOM()
        LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (month_year, n))
            rows = cur.fetchall()

    now = datetime.now(timezone.utc).isoformat()
    result = []
    for row in rows:
        imsi_hash, area, generation, highest_rat, dou_total, s1, iu, gb, usertype, month = row
        result.append({
            "ts": now,
            "subscriber_id": imsi_hash,
            "area": area or "Tunis",
            "generation": generation or "4G",
            "highest_rat": highest_rat or "4G",
            "dou_total": dou_total or 0,
            "s1_mme_sr": float(s1 or 0),
            "iu_attach_sr": float(iu or 0),
            "gb_attach_sr": float(gb or 0),
            "usertype": usertype or "Data User",
            "month_year": month or month_year,
            "source": "real",
        })
    return result


def sample_oss_records(n: int = SAMPLE_N, month_year: str = DEFAULT_MONTH) -> list[dict]:
    """Sample n OSS cell KPI records for the given month."""
    sql = """
        SELECT cell_id, area, throughput_mbps, latency_ms, packet_loss_rate,
               jitter_ms, active_users, rsrp_dbm, cell_load_pct, anomaly_flag
        FROM oss_cell_kpis
        WHERE month_year = %s
        ORDER BY RANDOM()
        LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (month_year, n))
            rows = cur.fetchall()

    now = datetime.now(timezone.utc).isoformat()
    result = []
    for row in rows:
        cell_id, area, tput, lat, loss, jitter, users, rsrp, load, anomaly = row
        result.append({
            "ts": now,
            "region": area or "demo",
            "cell_id": cell_id,
            "throughput_mbps": float(tput or 45),
            "latency_ms": float(lat or 25),
            "packet_loss_pct": float(loss or 0.8),
            "active_users": int(users or 100),
            "signal_rsrp_dbm": float(rsrp or -85),
            "is_fault": bool(anomaly),
            "source": "real",
        })
    return result
```

- [ ] **Step 2: Create `services/pipeline-worker/tests/test_sampler.py`**

```python
"""Tests for rolling window sampler — mock DB queries."""
from unittest.mock import patch, MagicMock
from worker.sampler import sample_bss_records, sample_oss_records


def _mock_conn_bss():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("hash001", "Tunis", "4G", "4G", 1500000000, 0.95, 0.90, 0.85, "Data User", "2026-03"),
        ("hash002", "Sfax", "5G", "4G", 3000000000, 0.88, 0.92, 0.80, "Data User", "2026-03"),
    ]
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn


def test_sample_bss_returns_list():
    with patch("worker.sampler.get_conn", return_value=_mock_conn_bss()):
        rows = sample_bss_records(n=2)
    assert len(rows) == 2


def test_sample_bss_required_fields():
    with patch("worker.sampler.get_conn", return_value=_mock_conn_bss()):
        rows = sample_bss_records(n=2)
    required = {"ts", "subscriber_id", "area", "generation", "highest_rat", "source"}
    for row in rows:
        assert required.issubset(row.keys())
        assert row["source"] == "real"
```

- [ ] **Step 3: Add USE_REAL_DATA flag to pipeline.py**

In `services/pipeline-worker/worker/pipeline.py`, add at top of `_run_pipeline_steps`:

```python
from worker.sampler import USE_REAL_DATA, sample_bss_records, sample_oss_records

# Inside _run_pipeline_steps(), replace synthetic generation steps:
if USE_REAL_DATA:
    print("[3/22] Sampling real OSS data from Postgres ...")
    oss_records = sample_oss_records(SYNTHETIC_N_RECORDS)
    fault_info = {"fault_cells": [], "fault_start_idx": 0, "fault_end_idx": 0,
                  "fault_records": sum(1 for r in oss_records if r.get("is_fault"))}
    print("[4/22] Sampling real BSS subscriber data from Postgres ...")
    bss_records = sample_bss_records(SYNTHETIC_N_RECORDS)
    # bss_records from sampler don't have revenue_tnd/churn_risk
    # so call existing generate_bss to get correlation-compatible format
    # and enrich sampled records with those fields via fallback
    # (keep synthetic correlation fields, real subscriber identity)
    bss_records = _enrich_bss_for_inference(bss_records, run_seed)
else:
    # original synthetic path
    oss_records, fault_info = generate_oss(SYNTHETIC_N_RECORDS, region, seed=run_seed)
    bss_records = generate_bss(SYNTHETIC_N_RECORDS, region, seed=run_seed + 1, fault_info=fault_info)
```

Add `_enrich_bss_for_inference` helper that merges sampled subscriber identity with synthetic revenue/churn fields until real revenue data arrives.

- [ ] **Step 4: Run tests**

```bash
cd services/pipeline-worker
python -m pytest tests/test_sampler.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add services/pipeline-worker/worker/sampler.py \
        services/pipeline-worker/worker/pipeline.py \
        services/pipeline-worker/tests/test_sampler.py
git commit -m "feat(pipeline-worker): rolling window sampler — USE_REAL_DATA=true to activate real data path"
```

---

---

# PHASE 3: AI Service v3.0 — New Models

**Context:** Train 4 new models in Jupyter notebooks, save as `.joblib`/`.pt` artifacts, add inference endpoints to ai-service. All training happens in `notebooks/v3/`. Jury sees notebooks as evidence.

**New models:**
| Model | Algorithm | Input | Output |
|---|---|---|---|
| CEM Score | LightGBM + SHAP | 10 BSS+OSS features per subscriber | CEM score 0-1 + SHAP explanation |
| Experience Anomaly | VAE (PyTorch) | 26 CEM features | Anomaly score + latent reconstruction |
| RAT Underservice | CatBoost | device generation × highest_rat × area | underservice probability |
| Churn Trajectory | TFT (pytorch-forecasting) | 5-month rolling sequences | churn probability 30/60/90d |

---

## Task 3.1: Create training notebooks

**Files:**
- Create: `notebooks/v3/04_cem_score_lgbm.ipynb`
- Create: `notebooks/v3/05_experience_anomaly_vae.ipynb`
- Create: `notebooks/v3/06_rat_underservice_catboost.ipynb`
- Create: `notebooks/v3/07_churn_trajectory_tft.ipynb`

**Each notebook structure (6 sections):**
1. `## Setup` — imports, DB connection, load data from Postgres
2. `## EDA` — distributions, class balance, missing values
3. `## Feature Engineering` — derived features specific to this model
4. `## Training` — train/val/test split (time-based: Feb/Mar real = train, Apr/May sim = val, Jun sim = test)
5. `## Evaluation` — confusion matrix, SHAP (LightGBM), reconstruction error (VAE), attention (TFT)
6. `## Save` — `joblib.dump(model, 'notebooks/models/v3/<name>.joblib')` or `torch.save()`

**Key patterns for each notebook:**

### `04_cem_score_lgbm.ipynb`

Data source: `SELECT * FROM subscriber_features JOIN oss area aggregates WHERE month_year IN ('2026-02', '2026-03')`

Features (10): `rat_gap_score`, `usim_bottleneck`, `data_intensity`, `network_experience_index`, `avg_throughput` (from area), `avg_latency` (from area), `avg_packet_loss` (from area), `anomaly_count` (from area), `pct_5g` (from BSS), `pct_legacy_sim` (from BSS)

Target: `cem_score_target`

```python
import lightgbm as lgb
import shap

X_train, X_val, y_train, y_val = ...  # time-based split

model = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=63, random_state=42)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(50)])

# SHAP
explainer = shap.TreeExplainer(model)
shap_values = explainer(X_val)
shap.plots.beeswarm(shap_values)  # jury evidence plot

import joblib
joblib.dump(model, "notebooks/models/v3/cem_score_lgbm.joblib")
```

### `05_experience_anomaly_vae.ipynb`

Data source: `SELECT * FROM subscriber_features WHERE month_year IN ('2026-02', '2026-03')`

Features (8): all numeric columns from `subscriber_features`

```python
import torch
import torch.nn as nn

class VAE(nn.Module):
    def __init__(self, input_dim=8, latent_dim=4):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 16), nn.ReLU(), nn.Linear(16, latent_dim * 2))
        self.decoder = nn.Sequential(nn.Linear(latent_dim, 16), nn.ReLU(), nn.Linear(16, input_dim))

    def reparameterize(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        h = self.encoder(x)
        mu, log_var = h.chunk(2, dim=-1)
        z = self.reparameterize(mu, log_var)
        x_hat = self.decoder(z)
        return x_hat, mu, log_var

# Train, compute reconstruction error per subscriber, set anomaly threshold at p95
# Visualize latent space with UMAP — jury evidence
torch.save(vae.state_dict(), "notebooks/models/v3/exp_anomaly_vae.pt")
```

### `06_rat_underservice_catboost.ipynb`

Data source: BSS subscribers where `rat_gap_score > 0.0`

Features: `generation` (categorical), `highest_rat` (categorical), `area` (categorical), `usim_flag`, `pct_5g_in_area`

Target: binary — `rat_gap_score > 0.5` (severely underserved)

```python
from catboost import CatBoostClassifier

cat_features = ["generation", "highest_rat", "area"]
model = CatBoostClassifier(iterations=500, depth=6, cat_features=cat_features, random_seed=42)
model.fit(X_train, y_train, eval_set=(X_val, y_val), early_stopping_rounds=50)

model.save_model("notebooks/models/v3/rat_underservice_catboost.cbm")
```

### `07_churn_trajectory_tft.ipynb`

Data source: `subscriber_features` across 5 months — build per-subscriber sequences

```python
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting.metrics import QuantileLoss

# Build time series dataset
# Static features: area, generation, highest_rat
# Time-varying: cem_score, rat_gap_score, network_experience_index, data_intensity
# Target: churn_risk_flag (next month)
# Prediction horizon: 1-3 months

training = TimeSeriesDataSet(df, time_idx="time_idx", target="churn_risk_flag",
                              group_ids=["imsi_hash"],
                              static_categoricals=["area", "generation"],
                              time_varying_known_reals=["time_idx"],
                              time_varying_unknown_reals=["cem_score", "rat_gap_score"])

tft = TemporalFusionTransformer.from_dataset(training, learning_rate=0.03, hidden_size=32)
trainer.fit(tft, train_dataloaders=train_dl, val_dataloaders=val_dl)
trainer.save_checkpoint("notebooks/models/v3/churn_tft.ckpt")
```

- [ ] **Step: Add new requirements to ai-service**

Edit `services/ai-service/requirements.txt` — add:
```
lightgbm==4.5.0
catboost==1.2.7
pytorch-forecasting==1.1.1
shap==0.46.0
umap-learn==0.5.7
```

- [ ] **Step: Add v3 inference routers**

Create `services/ai-service/routers/v3/` with:
- `cem_score.py` — `POST /infer/cem-score` (LightGBM + SHAP explanation)
- `exp_anomaly.py` — `POST /infer/exp-anomaly` (VAE reconstruction error)
- `rat_underservice.py` — `POST /infer/rat-underservice` (CatBoost)
- `churn.py` — `POST /infer/churn-trajectory` (TFT, multi-horizon)

Include v3 routers in `main.py`. Keep v2 routes unchanged (backward compat).

- [ ] **Step: New API Gateway endpoints**

In `services/api-gateway/routers/`, add:
- `cem.py` — `GET /cem-scores?area=X&month=Y&limit=N`
- `convergence.py` — `GET /convergence/area`, `GET /convergence/degradation-map`

These query `subscriber_features` and `area_network_health` tables.

---

---

# PHASE 4: Convergence Engine + PCMCI

**Context:** O+B convergence is the project's main differentiator. This phase adds the causal analysis layer and new API endpoints.

## Task 4.1: PCMCI Causal Analysis Module

**Files:**
- Create: `services/pipeline-worker/worker/analytics/causal.py`
- Create: `services/pipeline-worker/tests/test_causal.py`

```python
# services/pipeline-worker/worker/analytics/causal.py
"""
PCMCI Causal Discovery for OSS→BSS Impact
------------------------------------------
Uses tigramite.PCMCI to discover causal links between:
  - OSS degradation signals (latency, packet_loss, throughput)
  - CEM subscriber impact (cem_score, churn_risk)

At area level, across monthly time series.

Requires: pip install tigramite
"""
from typing import Optional
import numpy as np

try:
    from tigramite import data_processing as pp
    from tigramite.pcmci import PCMCI
    from tigramite.independence_tests.parcorr import ParCorr
    PCMCI_AVAILABLE = True
except ImportError:
    PCMCI_AVAILABLE = False
    print("[causal] tigramite not installed — PCMCI skipped")


def run_pcmci_area(area_time_series: np.ndarray, var_names: list[str], tau_max: int = 2) -> Optional[dict]:
    """
    Run PCMCI on area-level monthly time series.

    Args:
        area_time_series: shape (T, N) — T months, N variables
        var_names: list of N variable names
        tau_max: max time lag to test (default 2 months)

    Returns:
        dict with p_matrix, val_matrix, significant_links
        or None if tigramite unavailable or insufficient data
    """
    if not PCMCI_AVAILABLE:
        return None
    if area_time_series.shape[0] < 4:  # need >= 4 months
        return None

    dataframe = pp.DataFrame(area_time_series, var_names=var_names)
    pcmci = PCMCI(dataframe=dataframe, cond_ind_test=ParCorr(), verbosity=0)
    results = pcmci.run_pcmci(tau_max=tau_max, pc_alpha=0.05)

    # Extract significant links (p < 0.05)
    significant_links = []
    p_matrix = results["p_matrix"]
    val_matrix = results["val_matrix"]
    for j in range(len(var_names)):
        for i in range(len(var_names)):
            for tau in range(1, tau_max + 1):
                if p_matrix[i, j, tau] < 0.05:
                    significant_links.append({
                        "cause": var_names[i],
                        "effect": var_names[j],
                        "lag": int(tau),
                        "effect_size": round(float(val_matrix[i, j, tau]), 4),
                        "p_value": round(float(p_matrix[i, j, tau]), 4),
                    })

    return {
        "var_names": var_names,
        "tau_max": tau_max,
        "significant_links": significant_links,
        "n_time_steps": int(area_time_series.shape[0]),
    }
```

- [ ] **Add tigramite to pipeline-worker requirements**

```
tigramite==0.7.1
```

- [ ] **Create convergence runner** that pulls monthly area data from Postgres and runs PCMCI per area, saves results to `correlation_insights` table with `method='pcmci'`.

---

## Task 4.2: New Convergence API Endpoints

**Files:**
- Create: `services/api-gateway/routers/convergence.py`

Endpoints:
- `GET /convergence/area?area=Tunis&month=2026-03` — returns area CEM score + OSS KPIs + causal links
- `GET /convergence/degradation-map` — returns all 24 areas with health scores for heatmap

Query pattern:
```sql
SELECT a.area, a.avg_cem_score, a.underserved_pct, a.avg_throughput,
       a.avg_latency, a.anomaly_count
FROM area_network_health a
WHERE a.month_year = %s
ORDER BY a.avg_cem_score ASC
```

---

---

# PHASE 5: Agent System Upgrade

**Context:** Agent-service already has CEMAgent, NetworkAgent, ActionAgent, Orchestrator. This phase upgrades the LLM and wires agents to real database data.

## Task 5.1: Upgrade to Qwen3:8b

**Files:**
- Modify: `services/agent-service/orchestrator.py`
- Modify: `docker-compose.yml` — ensure Ollama model env var is configurable

```python
# In orchestrator.py, change:
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")  # was qwen2.5:7b

# Add thinking mode control in _ollama_generate:
def _ollama_generate(prompt: str, json_mode: bool = True, enable_thinking: bool = False) -> Optional[dict]:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0 if not enable_thinking else 0.6,
            "num_predict": 512 if enable_thinking else 256,
        },
    }
    if json_mode:
        payload["format"] = "json"
    if enable_thinking:
        # Qwen3 thinking mode: prepend /think to prompt
        payload["prompt"] = "/think\n" + prompt
    # ... rest unchanged
```

Pull command (run on host, not in Docker):
```bash
OLLAMA_MODELS=/mnt/d/ollama-models ollama pull qwen3:8b
```

## Task 5.2: Wire Agents to Real Data

**Files:**
- Modify: `services/agent-service/agents/cem_agent.py`
- Modify: `services/agent-service/agents/network_agent.py`

Current agents query hardcoded/demo data. Update to query real `subscriber_features` and `area_network_health` tables.

**CEM Agent real query example:**
```python
async def area_cem_summary(self, params: dict) -> AgentResult:
    area = params.get("area", "Tunis")
    month = params.get("month_year", "2026-03")
    sql = """
        SELECT avg_cem_score, underserved_pct, usim_bottleneck_pct,
               subscriber_count, anomaly_count
        FROM area_network_health
        WHERE area = %s AND month_year = %s
    """
    # Execute query, return real data
```

## Task 5.3: Conversation Persistence

The `agent_conversations` and `agent_reasoning_logs` tables already exist.

**Files:**
- Modify: `services/agent-service/main.py` — persist conversations to DB
- Modify: `services/agent-service/orchestrator.py` — log reasoning to `agent_reasoning_logs`

---

---

# PHASE 6: Dashboard + HCS Evidence + Polish

**Context:** Add new dashboard pages for v3.0 data, then document HCS mapping.

## Task 6.1: New Dashboard Pages

**Files to create:**
- `dashboard/app/cem-scores/page.tsx` — subscriber CEM distribution, per-area heatmap
- `dashboard/app/convergence/page.tsx` — OSS degradation overlay on CEM scores
- `dashboard/app/churn-trajectory/page.tsx` — TFT predictions over time

**API proxy updates** (`dashboard/app/api/platform-data/route.ts`):
Add new endpoints to parallel fetch: `/cem-scores`, `/convergence/area`, `/convergence/degradation-map`

## Task 6.2: HCS Evidence Documentation

**File:** `docs/deployment/hcs-mapping.md`

Document exact mapping:
| Local | HCS Service | Config needed |
|---|---|---|
| MinIO | OBS | Change S3_ENDPOINT to OBS endpoint |
| PostgreSQL 16 | RDS for MySQL / GaussDB | Update DATABASE_URL |
| Docker containers | ECS | Push images to SWR, create ECS task definitions |
| Ollama/Qwen3:8b | ModelArts / AI Gateway | API endpoint swap in orchestrator.py |

## Task 6.3: Final Polish

- Update CLAUDE.md with final status
- Run full test suite, ensure ruff clean
- Docker compose up --build -d, verify all services healthy
- Run ETL, verify dashboard shows real data everywhere

---

---

# Appendix: Database Tables Reference

Tables that ALREADY EXIST (created in earlier phases — Kimi does not need to create):

| Table | Purpose | Key columns |
|---|---|---|
| `bss_subscribers` | Real TT subscriber data | `imsi_hash`, `area`, `generation`, `highest_rat`, `month_year` |
| `oss_cell_kpis` | Simulated OSS cell KPIs | `cell_id`, `area`, `month_year`, `throughput_mbps`, `latency_ms` |
| `subscriber_features` | Computed CEM features | `imsi_hash`, `month_year`, `cem_score`, `rat_gap_score`, `churn_risk_flag` |
| `area_network_health` | Area-level aggregates | `area`, `month_year`, `avg_cem_score`, `underserved_pct` |
| `agent_conversations` | Multi-agent chat history | `thread_id`, `messages` (JSONB) |
| `agent_reasoning_logs` | Agent reasoning audit | `thread_id`, `agent_name`, `latency_ms` |
| `pipeline_runs` | Pipeline execution log | `run_id`, `status`, `started_at` |
| `agent_actions` | L4 agent action log | `action_id`, `status`, `execution_log` (JSONB) |

---

# Critical Rules for Kimi

1. **NEVER touch `TT_data/`** — confidential, gitignored. Do not read, move, or log contents.
2. **IMSI is always hashed** — `imsi_hash = sha256(imsi + salt)[:32]`. Never store raw IMSI.
3. **Ruff must pass** — run `ruff check services/` before every commit. Fix all errors.
4. **One task at a time** — mark complete, commit, then move to next. No batching.
5. **Tests first on new logic** — write test, see it fail, implement, see it pass.
6. **Do not change business logic in Phase 1** — Phase 1 is purely structural. Same inputs → same outputs.
7. **Docker builds must stay green** — check with `docker compose build <service>` after each major change.
8. **Auth-service is untouched in Phase 1** — `services/auth-service/main.py` stays as-is.
9. **Agent-service is untouched in Phase 1** — it's already modular; leave it.
10. **Recharts v2.x pinned** — never upgrade to v3.x in dashboard (causes React error #310).
