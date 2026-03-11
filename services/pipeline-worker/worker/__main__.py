"""
Pipeline Worker — Phase 3 (22-step execution)
Sequence:
  1.  Ensure MinIO buckets exist (raw / processed / curated layers)
  2.  Generate synthetic OSS dataset (with fault injection)
  3.  Generate synthetic BSS dataset (with correlated revenue dips)
  4.  Upload OSS raw to MinIO
  5.  Upload BSS raw to MinIO
  6.  Insert pipeline_runs record
  7.  Register raw datasets in dataset_registry
  8.  Process OSS data → upload to processed bucket
  9.  Process BSS data → upload to processed bucket
  10. Register processed datasets
  11. Compute aggregate KPI features (OSS + BSS)
  12. Call AI service /infer/sla-risk
  13. Call AI service /infer/anomaly (OSS IsolationForest)
  14. Call AI service /infer/revenue-anomaly (BSS IsolationForest)
  15. Compute OSS↔BSS correlations (Pearson + Spearman)
  16. Build curated dataset (joined OSS+BSS+AI) → upload to curated bucket
  17. Register curated dataset
  18. Persist SLA risk score
  19. Persist OSS anomalies
  20. Persist revenue anomalies
  21. Register models in model_registry
  22. Persist correlation insights + mark pipeline succeeded
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from io import BytesIO

import boto3
import numpy as np
import psycopg2
import psycopg2.extras
import requests

# ── helpers ──────────────────────────────────────────────────────────────────

def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(db_url)


def get_s3():
    endpoint = os.getenv("S3_ENDPOINT", "http://minio:9000")
    access   = os.getenv("S3_ACCESS_KEY", "minio")
    secret   = os.getenv("S3_SECRET_KEY", "minio_pw")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
    )


def ensure_buckets(s3, buckets: list[str]) -> None:
    existing = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
    for bucket in buckets:
        if bucket not in existing:
            s3.create_bucket(Bucket=bucket)
            print(f"  created bucket: {bucket}")
        else:
            print(f"  bucket exists:  {bucket}")


# ── synthetic data generators ────────────────────────────────────────────────

def generate_oss(n: int = 200, region: str = "demo", seed: int = 42) -> tuple[list[dict], dict]:
    """Synthetic OSS KPI records with realistic fault injection.

    Patterns:
      - Business-hour load curves (Gaussian peak at 13:00 local)
      - Fault injection: 2–3 random cells experience degradation for ~20 % of window
      - Degradation: throughput collapse, latency spike, packet loss surge, signal drop

    Returns (records, fault_info) describing injected faults.
    """
    rng   = np.random.default_rng(seed)
    cells = [f"CELL-{i:03d}" for i in range(1, 11)]
    now   = datetime.now(timezone.utc)

    # ── fault injection plan ───────────────────────────────────────────────
    n_fault_cells  = int(rng.integers(2, 4))
    fault_cells    = set(rng.choice(cells, size=n_fault_cells, replace=False))
    fault_start    = int(n * rng.uniform(0.25, 0.45))
    fault_duration = int(n * rng.uniform(0.15, 0.25))
    fault_end      = min(n - 1, fault_start + fault_duration)

    rows = []
    for i in range(n):
        ts   = now - timedelta(minutes=n - i)
        cell = cells[i % len(cells)]

        # ── business-hour traffic modifier ─────────────────────────────────
        hour       = ts.hour + ts.minute / 60.0
        biz_factor = 1.0 + 0.4 * np.exp(-0.5 * ((hour - 13.0) / 3.0) ** 2)

        # ── base KPIs (normal conditions) ──────────────────────────────────
        tput = float(rng.normal(80, 12)) * (0.7 + 0.3 / biz_factor)
        lat  = float(rng.normal(22, 6))  * biz_factor
        loss = float(rng.uniform(0, 1.5)) * biz_factor
        usr  = int(rng.integers(50, 300) * biz_factor)
        rsrp = float(rng.normal(-82, 8))

        # ── fault injection ───────────────────────────────────────────────
        is_fault = (cell in fault_cells) and (fault_start <= i <= fault_end)
        if is_fault:
            tput *= float(rng.uniform(0.10, 0.35))       # throughput collapse
            lat  *= float(rng.uniform(2.5,  5.0))        # latency spike
            loss += float(rng.uniform(3.0,  8.0))        # packet loss surge
            rsrp -= float(rng.uniform(15,  30))           # signal degradation

        rows.append({
            "ts":              ts.isoformat(),
            "region":          region,
            "cell_id":         cell,
            "throughput_mbps": float(round(max(0.1, tput), 2)),
            "latency_ms":      float(round(max(1.0, lat), 2)),
            "packet_loss_pct": float(round(min(15.0, max(0.0, loss)), 4)),
            "active_users":    max(10, usr),
            "signal_rsrp_dbm": float(round(max(-140.0, min(-40.0, rsrp)), 2)),
            "is_fault":        is_fault,
        })

    fault_info = {
        "fault_cells":     sorted(fault_cells),
        "fault_start_idx": fault_start,
        "fault_end_idx":   fault_end,
        "fault_records":   sum(1 for r in rows if r["is_fault"]),
    }
    return rows, fault_info


def generate_bss(n: int = 200, region: str = "demo", seed: int = 99,
                 cells: list[str] | None = None,
                 fault_info: dict | None = None) -> list[dict]:
    """Synthetic BSS records with correlated degradation patterns.

    Tunisian market model (verified 2025 forfait data):
      - 80% prepaid subscribers (recharge/forfait-based revenue)
      - 20% postpaid subscribers (fixed monthly plan)
      - Revenue in TND based on verified operator pricing
      - Prepaid ARPU: ~8-15 TND/month; Postpaid ARPU: ~45-70 TND/month

    When a subscriber’s serving cell is in a fault state, BSS metrics degrade:
    lower data usage, higher churn risk, fewer voice minutes — creating a
    measurable OSS↔BSS correlation.
    """
    rng       = np.random.default_rng(seed)
    operators = ["Ooredoo Tunisie", "Tunisie Telecom", "Orange Tunisie"]
    if cells is None:
        cells = [f"CELL-{i:03d}" for i in range(1, 11)]

    # Prepaid forfait tiers — verified 2025 pricing (all 3 operators converge)
    prepaid_plans = [
        ("data_1go",    3.0,   7.0),   # ~4-5 DT: light users, 1-1.5 Go bundles
        ("data_4go",    8.0,  14.0),   # ~10 DT: mid-tier 4 Go
        ("data_6go",   12.0,  18.0),   # ~15 DT: 6 Go
        ("data_25go",  25.0,  35.0),   # ~30 DT: standard 5G/4G bundle
        ("data_45go",  42.0,  55.0),   # ~50 DT: heavy user
        ("data_100go", 65.0,  80.0),   # ~72 DT: very heavy user
    ]
    # Postpaid plan tiers — verified ranges across operators
    postpaid_plans = [
        ("post_40",  35.0,  45.0),     # entry postpaid ~40 DT/month
        ("post_60",  52.0,  68.0),     # mid postpaid ~60 DT/month
        ("post_90",  80.0, 100.0),     # premium postpaid ~90 DT/month
    ]

    fault_cells     = set(fault_info["fault_cells"]) if fault_info else set()
    fault_start_idx = fault_info["fault_start_idx"]  if fault_info else 0
    fault_end_idx   = fault_info["fault_end_idx"]    if fault_info else 0

    now  = datetime.now(timezone.utc)
    rows = []
    for i in range(n):
        ts           = now - timedelta(minutes=n - i)
        serving_cell = cells[i % len(cells)]

        # 80% prepaid / 20% postpaid (matches INTT 2023 market stats)
        is_prepaid = rng.random() < 0.80
        if is_prepaid:
            plan_name, lo, hi = prepaid_plans[int(rng.integers(0, len(prepaid_plans)))]
            line_type = "prepaid"
        else:
            plan_name, lo, hi = postpaid_plans[int(rng.integers(0, len(postpaid_plans)))]
            line_type = "postpaid"

        base_revenue = float(rng.uniform(lo, hi))
        base_data    = float(rng.uniform(0.5, 45.0))
        base_voice   = int(rng.integers(10, 550))
        base_sms     = int(rng.integers(5, 180))
        base_churn   = float(rng.uniform(0.0, 0.35))

        # ── correlated BSS degradation ───────────────────────────────────────────
        cell_faulted = (serving_cell in fault_cells
                        and fault_start_idx <= i <= fault_end_idx)
        if cell_faulted:
            base_data  *= float(rng.uniform(0.3, 0.6))      # data usage drops
            base_voice  = int(base_voice * rng.uniform(0.4, 0.7))
            base_churn += float(rng.uniform(0.3, 0.55))     # churn risk spikes

        rows.append({
            "ts":            ts.isoformat(),
            "region":        region,
            "operator":      operators[i % len(operators)],
            "subscriber_id": f"TN-{rng.integers(100000, 999999)}",
            "line_type":     line_type,
            "plan":          plan_name,
            "serving_cell":  serving_cell,
            "revenue_tnd":   float(round(base_revenue, 3)),
            "data_used_gb":  float(round(max(0.01, base_data), 3)),
            "voice_min":     max(0, base_voice),
            "sms_count":     base_sms,
            "churn_risk":    float(round(min(1.0, base_churn), 4)),
        })
    return rows


# ── MinIO upload ──────────────────────────────────────────────────────────────

def upload_json(s3, bucket: str, key: str, records: list[dict]) -> None:
    body = json.dumps(records, indent=2).encode()
    s3.put_object(Bucket=bucket, Key=key, Body=BytesIO(body), ContentLength=len(body))
    print(f"  uploaded s3://{bucket}/{key}  ({len(records)} records, {len(body):,} bytes)")


# ── feature engineering ──────────────────────────────────────────────────────

def compute_oss_features(records: list[dict]) -> dict:
    """Aggregate 200 per-record OSS measurements into the 9 features the
    SLA risk model was trained on."""
    tput = np.array([r["throughput_mbps"]  for r in records], dtype=float)
    lat  = np.array([r["latency_ms"]       for r in records], dtype=float)
    loss = np.array([r["packet_loss_pct"]  for r in records], dtype=float)
    usr  = np.array([r["active_users"]     for r in records], dtype=float)
    rsrp = np.array([r["signal_rsrp_dbm"] for r in records], dtype=float)
    return {
        "mean_throughput_mbps":  round(float(tput.mean()), 4),
        "std_throughput_mbps":   round(float(tput.std()),  4),
        "mean_latency_ms":       round(float(lat.mean()),  4),
        "std_latency_ms":        round(float(lat.std()),   4),
        "max_latency_ms":        round(float(lat.max()),   4),
        "mean_packet_loss_pct":  round(float(loss.mean()), 4),
        "max_packet_loss_pct":   round(float(loss.max()),  4),
        "mean_active_users":     round(float(usr.mean()),  4),
        "mean_signal_rsrp_dbm":  round(float(rsrp.mean()), 4),
    }


def compute_bss_features(records: list[dict]) -> dict:
    """Aggregate BSS metrics for revenue anomaly context."""
    rev   = np.array([r["revenue_tnd"]  for r in records], dtype=float)
    data  = np.array([r["data_used_gb"] for r in records], dtype=float)
    voice = np.array([r["voice_min"]    for r in records], dtype=float)
    sms   = np.array([r["sms_count"]    for r in records], dtype=float)
    churn = np.array([r["churn_risk"]   for r in records], dtype=float)
    return {
        "mean_revenue_tnd":  round(float(rev.mean()), 4),
        "std_revenue_tnd":   round(float(rev.std()), 4),
        "mean_data_used_gb": round(float(data.mean()), 4),
        "mean_voice_min":    round(float(voice.mean()), 4),
        "mean_sms_count":    round(float(sms.mean()), 4),
        "mean_churn_risk":   round(float(churn.mean()), 4),
    }


# ── data processing (processed / curated layers) ─────────────────────────────

def build_processed_oss(records: list[dict]) -> list[dict]:
    """Clean + enrich OSS records for the processed data-lake layer."""
    processed = []
    for r in records:
        lat  = r["latency_ms"]
        tput = r["throughput_mbps"]
        loss = r["packet_loss_pct"]
        usr  = r["active_users"]

        lat_severity  = ("critical" if lat > 80 else
                         "high" if lat > 50 else
                         "medium" if lat > 30 else "normal")
        tput_category = ("degraded" if tput < 20 else
                         "fair" if tput < 50 else "good")
        load_factor   = round(usr / 500.0, 4) if usr else 0.0
        qos_score     = round(max(0.0, 1.0 - (lat / 100) - (loss / 10)
                                   + (tput / 200)), 4)

        rec = {k: v for k, v in r.items() if k != "is_fault"}
        rec.update({
            "latency_severity":   lat_severity,
            "throughput_category": tput_category,
            "load_factor":        load_factor,
            "qos_score":          qos_score,
        })
        processed.append(rec)
    return processed


def build_processed_bss(records: list[dict]) -> list[dict]:
    """Clean + enrich BSS records for the processed data-lake layer."""
    processed = []
    for r in records:
        rec = dict(r)
        rev = r["revenue_tnd"]
        # ARPU categories aligned to Tunisian recharge patterns
        rec["arpu_category"]  = ("low" if rev < 10
                                 else "mid" if rev < 40
                                 else "high")
        rec["data_intensity"] = round(r["data_used_gb"]
                                      / max(rev, 0.01), 4)
        rec["churn_bucket"]   = ("safe" if r["churn_risk"] < 0.3
                                 else "watch" if r["churn_risk"] < 0.6
                                 else "risk")
        processed.append(rec)
    return processed


def build_curated_dataset(oss_records, bss_records, anomaly_result,
                          rev_anomaly_result, sla_score, correlations):
    """Build the final curated dataset joining OSS + BSS + AI outputs."""
    cell_oss = {}
    for r in oss_records:
        cid = r["cell_id"]
        if cid not in cell_oss:
            cell_oss[cid] = {"tput": [], "lat": [], "loss": [], "rsrp": []}
        cell_oss[cid]["tput"].append(r["throughput_mbps"])
        cell_oss[cid]["lat"].append(r["latency_ms"])
        cell_oss[cid]["loss"].append(r["packet_loss_pct"])
        cell_oss[cid]["rsrp"].append(r["signal_rsrp_dbm"])

    cell_bss = {}
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
            "cell_id":          cid,
            "mean_throughput":  round(float(np.mean(oss.get("tput", [0]))), 2),
            "mean_latency":     round(float(np.mean(oss.get("lat", [0]))), 2),
            "mean_packet_loss": round(float(np.mean(oss.get("loss", [0]))), 4),
            "mean_revenue_tnd": round(float(np.mean(bss.get("rev", [0]))), 2),
            "mean_data_gb":     round(float(np.mean(bss.get("data", [0]))), 2),
            "mean_churn_risk":  round(float(np.mean(bss.get("churn", [0]))), 4),
        })

    return {
        "sla_risk_score":    sla_score,
        "oss_anomaly_count": anomaly_result.get("anomalous_count", 0),
        "bss_anomaly_count": rev_anomaly_result.get("anomalous_count", 0),
        "correlations":      correlations,
        "cells_summary":     cells_summary,
        "total_oss_records": len(oss_records),
        "total_bss_records": len(bss_records),
    }


def compute_correlations(oss_records, bss_records):
    """Compute Pearson + Spearman correlations between OSS and BSS per cell."""
    from scipy import stats

    cell_oss = {}
    for r in oss_records:
        cid = r["cell_id"]
        if cid not in cell_oss:
            cell_oss[cid] = {"lat": [], "tput": [], "loss": []}
        cell_oss[cid]["lat"].append(r["latency_ms"])
        cell_oss[cid]["tput"].append(r["throughput_mbps"])
        cell_oss[cid]["loss"].append(r["packet_loss_pct"])

    cell_bss = {}
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

    oss_lat  = np.array([np.mean(cell_oss[c]["lat"])  for c in common])
    oss_tput = np.array([np.mean(cell_oss[c]["tput"]) for c in common])
    oss_loss = np.array([np.mean(cell_oss[c]["loss"]) for c in common])
    bss_rev  = np.array([np.mean(cell_bss[c]["rev"])  for c in common])
    bss_data = np.array([np.mean(cell_bss[c]["data"]) for c in common])
    bss_churn = np.array([np.mean(cell_bss[c]["churn"]) for c in common])

    pairs = [
        ("mean_latency_ms",      "mean_revenue_tnd",  oss_lat,  bss_rev),
        ("mean_throughput_mbps", "mean_data_used_gb", oss_tput, bss_data),
        ("mean_packet_loss_pct", "mean_churn_risk",   oss_loss, bss_churn),
        ("mean_latency_ms",      "mean_churn_risk",   oss_lat,  bss_churn),
        ("mean_throughput_mbps", "mean_revenue_tnd",  oss_tput, bss_rev),
    ]

    results = []
    for metric_x, metric_y, arr_x, arr_y in pairs:
        for method in ("pearson", "spearman"):
            if method == "pearson":
                corr_val, p_val = stats.pearsonr(arr_x, arr_y)
            else:
                corr_val, p_val = stats.spearmanr(arr_x, arr_y)
            results.append({
                "metric_x":   metric_x,
                "metric_y":   metric_y,
                "method":     method,
                "corr_value": round(float(corr_val), 6),
                "p_value":    round(float(p_val), 6),
            })
    return results


# ── AI inference ──────────────────────────────────────────────────────────────

def infer_sla_risk(run_id: str, region: str, window_start: datetime,
                   window_end: datetime, features: dict) -> tuple[float, dict, str]:
    base    = os.getenv("AI_SERVICE_URL", "http://ai-service:8001").rstrip("/")
    payload = {
        "run_id":       run_id,
        "region":       region,
        "window_start": window_start.isoformat(),
        "window_end":   window_end.isoformat(),
        "features":     features,
    }
    r = requests.post(f"{base}/infer/sla-risk", json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    return float(data["score"]), data.get("explanation", {}), data.get("model_version", "v1.0")


def infer_anomaly(run_id: str, region: str, records: list[dict]) -> dict:
    base    = os.getenv("AI_SERVICE_URL", "http://ai-service:8001").rstrip("/")
    # send only the 5 numeric KPI fields the anomaly model expects
    payload = {
        "run_id":  run_id,
        "region":  region,
        "records": [
            {
                "throughput_mbps":   r["throughput_mbps"],
                "latency_ms":        r["latency_ms"],
                "packet_loss_pct":   r["packet_loss_pct"],
                "active_users":      r["active_users"],
                "signal_rsrp_dbm":   r["signal_rsrp_dbm"],
            }
            for r in records
        ],
    }
    r = requests.post(f"{base}/infer/anomaly", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


# ── main pipeline ─────────────────────────────────────────────────────────────
def infer_revenue_anomaly(run_id: str, region: str, records: list[dict]) -> dict:
    """Call AI service /infer/revenue-anomaly with BSS records."""
    base = os.getenv("AI_SERVICE_URL", "http://ai-service:8001").rstrip("/")
    payload = {
        "run_id": run_id,
        "region": region,
        "records": [
            {
                "revenue_tnd":  r["revenue_tnd"],
                "data_used_gb": r["data_used_gb"],
                "voice_min":    float(r["voice_min"]),
                "sms_count":    float(r["sms_count"]),
                "churn_risk":   r["churn_risk"],
            }
            for r in records
        ],
    }
    r = requests.post(f"{base}/infer/revenue-anomaly", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def run_once() -> None:
    run_id       = f"run-{uuid.uuid4().hex[:12]}"
    now          = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=15)
    window_end   = now
    region       = "demo"

    # Derive reproducible seed from run_id (different data each run)
    run_seed = int(hashlib.sha256(run_id.encode()).hexdigest()[:8], 16) % (2**31)

    print(f"\n[pipeline] run_id={run_id}  seed={run_seed}")

    # ── 1. MinIO buckets ───────────────────────────────────────────────
    print("[1/22] Ensuring MinIO buckets ...")
    s3 = get_s3()
    ensure_buckets(s3, ["raw", "processed", "curated"])

    # ── 2–3. Synthetic data with fault injection ─────────────────────────
    print("[2/22] Generating synthetic OSS data (with fault injection) ...")
    oss_records, fault_info = generate_oss(200, region, seed=run_seed)
    print(f"  {len(oss_records)} OSS records — "
          f"faults: {fault_info['fault_records']} records on cells {fault_info['fault_cells']}")

    print("[3/22] Generating synthetic BSS data (with correlated dips) ...")
    bss_records = generate_bss(200, region, seed=run_seed + 1, fault_info=fault_info)
    print(f"  {len(bss_records)} BSS records generated")

    # ── 4–5. Upload raw layer ────────────────────────────────────────────
    date_prefix = now.strftime("%Y/%m/%d")
    oss_key = f"oss/{date_prefix}/{run_id}.json"
    bss_key = f"bss/{date_prefix}/{run_id}.json"

    print("[4/22] Uploading OSS dataset to MinIO raw layer ...")
    upload_json(s3, "raw", oss_key, oss_records)

    print("[5/22] Uploading BSS dataset to MinIO raw layer ...")
    upload_json(s3, "raw", bss_key, bss_records)

    with get_conn() as conn:
        with conn.cursor() as cur:

            # ── 6. pipeline_runs ─────────────────────────────────────────
            print("[6/22] Inserting pipeline_runs record ...")
            cur.execute(
                "INSERT INTO pipeline_runs (run_id, status) VALUES (%s, %s);",
                (run_id, "started"),
            )

            # ── 7. dataset_registry (raw) ─────────────────────────────────
            print("[7/22] Registering raw datasets ...")
            for ds_type, key, count in [
                ("oss", oss_key, len(oss_records)),
                ("bss", bss_key, len(bss_records)),
            ]:
                cur.execute(
                    """INSERT INTO dataset_registry
                         (run_id, dataset_type, layer, format, object_key, row_count)
                       VALUES (%s, %s, %s, %s, %s, %s);""",
                    (run_id, ds_type, "raw", "json", key, count),
                )

            # ── 8–9. Processed layer ───────────────────────────────────────
            print("[8/22] Processing OSS data → processed layer ...")
            proc_oss = build_processed_oss(oss_records)
            proc_oss_key = f"oss/{date_prefix}/{run_id}_processed.json"
            upload_json(s3, "processed", proc_oss_key, proc_oss)

            print("[9/22] Processing BSS data → processed layer ...")
            proc_bss = build_processed_bss(bss_records)
            proc_bss_key = f"bss/{date_prefix}/{run_id}_processed.json"
            upload_json(s3, "processed", proc_bss_key, proc_bss)

            # ── 10. Register processed datasets ───────────────────────────
            print("[10/22] Registering processed datasets ...")
            for ds_type, key, count in [
                ("oss", proc_oss_key, len(proc_oss)),
                ("bss", proc_bss_key, len(proc_bss)),
            ]:
                cur.execute(
                    """INSERT INTO dataset_registry
                         (run_id, dataset_type, layer, format, object_key, row_count)
                       VALUES (%s, %s, %s, %s, %s, %s);""",
                    (run_id, ds_type, "processed", "json", key, count),
                )

            # ── 11. Feature engineering ──────────────────────────────────
            print("[11/22] Computing aggregate KPI features ...")
            features = compute_oss_features(oss_records)
            bss_features = compute_bss_features(bss_records)
            print(f"  OSS: mean_lat={features['mean_latency_ms']}ms  "
                  f"mean_loss={features['mean_packet_loss_pct']}%  "
                  f"mean_tput={features['mean_throughput_mbps']}Mbps")
            print(f"  BSS: mean_rev={bss_features['mean_revenue_tnd']}TND  "
                  f"mean_churn={bss_features['mean_churn_risk']}")

            # ── 12. SLA risk inference ───────────────────────────────────
            print("[12/22] Calling AI service /infer/sla-risk ...")
            score, explanation, model_version = infer_sla_risk(
                run_id, region, window_start, window_end, features
            )
            print(f"  risk_score={score}  model={model_version}")

            # ── 13. OSS anomaly detection ────────────────────────────────
            print("[13/22] Calling AI service /infer/anomaly ...")
            anomaly_result = infer_anomaly(run_id, region, oss_records)
            print(f"  OSS anomalies: {anomaly_result['anomalous_count']}/{len(oss_records)}  "
                  f"rate={anomaly_result['anomaly_rate']}")

            # ── 14. Revenue anomaly detection ────────────────────────────
            print("[14/22] Calling AI service /infer/revenue-anomaly ...")
            rev_anomaly_result = infer_revenue_anomaly(run_id, region, bss_records)
            print(f"  BSS anomalies: {rev_anomaly_result['anomalous_count']}/{len(bss_records)}  "
                  f"rate={rev_anomaly_result['anomaly_rate']}")

            # ── 15. OSS↔BSS correlations ───────────────────────────────
            print("[15/22] Computing OSS↔BSS correlations ...")
            correlations = compute_correlations(oss_records, bss_records)
            for c in correlations:
                print(f"  {c['method']:>8s}  {c['metric_x']:<28s} ↔ {c['metric_y']:<22s}  "
                      f"r={c['corr_value']:+.4f}  p={c['p_value']:.4f}")

            # ── 16. Curated dataset ──────────────────────────────────────
            print("[16/22] Building curated dataset → curated layer ...")
            curated = build_curated_dataset(
                oss_records, bss_records,
                anomaly_result, rev_anomaly_result,
                score, correlations,
            )
            curated_key = f"joined/{date_prefix}/{run_id}_curated.json"
            upload_json(s3, "curated", curated_key, [curated])

            # ── 17. Register curated dataset ─────────────────────────────
            print("[17/22] Registering curated dataset ...")
            cur.execute(
                """INSERT INTO dataset_registry
                     (run_id, dataset_type, layer, format, object_key, row_count)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (run_id, "curated", "curated", "json", curated_key, 1),
            )

            # ── 18. Persist SLA risk score ───────────────────────────────
            print("[18/22] Persisting SLA risk score ...")
            cur.execute(
                """INSERT INTO sla_risk_scores
                     (run_id, region, window_start, window_end, score,
                      explanation, model_version)
                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (run_id, region, window_start, window_end, score,
                 psycopg2.extras.Json(explanation), model_version),
            )

            # ── 19. Persist OSS anomalies ────────────────────────────────
            print("[19/22] Persisting OSS anomalies ...")
            oss_anom_records = [r for r in anomaly_result["records"] if r["is_anomaly"]]
            for anom in oss_anom_records:
                idx = anom["index"]
                src = oss_records[idx]
                cur.execute(
                    """INSERT INTO anomalies
                         (run_id, ts, region, cell_id, kpi_name, severity,
                          value, baseline_value, model_version)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (run_id, src["ts"], src["region"], src["cell_id"],
                     "composite_kpi", round(anom["anomaly_score"], 4),
                     src["latency_ms"], 25.0,
                     anomaly_result.get("model_version", "v2.0")),
                )

            # ── 20. Persist revenue anomalies ────────────────────────────
            print("[20/22] Persisting revenue anomalies ...")
            bss_anom_records = [r for r in rev_anomaly_result["records"]
                                if r["is_anomaly"]]
            for anom in bss_anom_records:
                idx = anom["index"]
                src = bss_records[idx]
                cur.execute(
                    """INSERT INTO revenue_anomalies
                         (run_id, ts, region, operator, subscriber_id,
                          line_type, plan,
                          metric_name, severity, value, baseline_value,
                          model_version)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (run_id, src["ts"], src["region"], src["operator"],
                     src["subscriber_id"], src["line_type"], src["plan"],
                     "composite_bss", round(anom["anomaly_score"], 4),
                     src["revenue_tnd"], bss_features["mean_revenue_tnd"],
                     rev_anomaly_result.get("model_version", "v2.0")),
                )

            # ── 21. Register models ──────────────────────────────────────
            print("[21/22] Registering models in model_registry ...")
            for mname, mver in [
                ("sla-risk", "v2.0"),
                ("anomaly", "v2.0"),
                ("revenue-anomaly", "v2.0"),
            ]:
                cur.execute(
                    """INSERT INTO model_registry
                         (model_name, version, artifact_object_key)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (model_name, version) DO NOTHING;""",
                    (mname, mver, f"models/{mname}_{mver}.joblib"),
                )

            # ── 22. Persist correlations + finish ─────────────────────────
            print("[22/22] Persisting correlation insights ...")
            for c in correlations:
                cur.execute(
                    """INSERT INTO correlation_insights
                         (run_id, region, metric_x, metric_y,
                          window_start, window_end, method,
                          corr_value, p_value)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (run_id, region, c["metric_x"], c["metric_y"],
                     window_start, window_end, c["method"],
                     c["corr_value"], c["p_value"]),
                )

            # ── mark succeeded ──────────────────────────────────────────
            cur.execute(
                "UPDATE pipeline_runs SET status=%s, finished_at=now() "
                "WHERE run_id=%s;",
                ("succeeded", run_id),
            )

    print(f"\n[pipeline] ✓ run {run_id} succeeded")
    print(f"  SLA risk:        {score:.4f}")
    print(f"  OSS anomalies:   {anomaly_result['anomalous_count']}/{len(oss_records)}")
    print(f"  BSS anomalies:   {rev_anomaly_result['anomalous_count']}/{len(bss_records)}")
    print(f"  Correlations:    {len(correlations)} computed")
    print(f"  Fault injection: {fault_info['fault_records']} records on {fault_info['fault_cells']}")



def main() -> None:
    print("pipeline-worker: starting vertical slice execution")
    run_once()
    print("pipeline-worker: execution complete")


if __name__ == "__main__":
    main()
