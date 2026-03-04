"""
Pipeline Worker — Vertical Slice
Sequence:
  1.  Ensure MinIO buckets exist (raw / processed / curated layers)
  2.  Generate synthetic OSS dataset (network KPIs)
  3.  Generate synthetic BSS dataset (revenue / usage, TND, Tunisian operators)
  4.  Upload both datasets to MinIO raw layer
  5.  Insert pipeline_runs record
  6.  Insert dataset_registry records
  7.  Compute aggregate KPI features from OSS data
  8.  Call AI service /infer/sla-risk with real GradientBoosting features
  9.  Call AI service /infer/anomaly (IsolationForest on per-record KPIs)
  10. Persist sla_risk_scores to PostgreSQL
  11. Persist individual anomalies to PostgreSQL
  12. Mark pipeline_run as succeeded
"""

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

def generate_oss(n: int = 200, region: str = "demo", seed: int = 42) -> list[dict]:
    """Synthetic OSS KPI records — cell tower measurements."""
    rng = np.random.default_rng(seed)
    cells = [f"CELL-{i:03d}" for i in range(1, 11)]
    now   = datetime.now(timezone.utc)
    rows  = []
    for i in range(n):
        ts = now - timedelta(minutes=n - i)
        rows.append({
            "ts":              ts.isoformat(),
            "region":          region,
            "cell_id":         cells[i % len(cells)],
            "throughput_mbps": float(round(max(0.0, rng.normal(80, 15)), 2)),
            "latency_ms":      float(round(max(1.0, rng.normal(25, 8)), 2)),
            "packet_loss_pct": float(round(float(rng.uniform(0, 3)), 4)),
            "active_users":    int(rng.integers(50, 500)),
            "signal_rsrp_dbm": float(round(float(rng.normal(-85, 10)), 2)),
        })
    return rows


def generate_bss(n: int = 200, region: str = "demo", seed: int = 99) -> list[dict]:
    """Synthetic BSS records — revenue and data consumption per subscriber.

    Operators: the three Tunisian mobile operators.
    Revenue in TND (Tunisian Dinar) — realistic retail plan ranges:
      basic    15–35 TND/month
      standard 35–75 TND/month
      premium  75–150 TND/month
    """
    rng       = np.random.default_rng(seed)
    plans     = ["basic", "standard", "premium"]
    operators = ["Ooredoo Tunisie", "Tunisie Telecom", "Orange Tunisie"]
    # revenue bands per plan (min, max) in TND
    revenue_bands = {
        "basic":    (15.0,  35.0),
        "standard": (35.0,  75.0),
        "premium":  (75.0, 150.0),
    }
    now  = datetime.now(timezone.utc)
    rows = []
    for i in range(n):
        ts   = now - timedelta(minutes=n - i)
        plan = plans[i % len(plans)]
        lo, hi = revenue_bands[plan]
        rows.append({
            "ts":            ts.isoformat(),
            "region":        region,
            "operator":      operators[i % len(operators)],
            "subscriber_id": f"TN-{rng.integers(100000, 999999)}",
            "plan":          plan,
            "revenue_tnd":   float(round(float(rng.uniform(lo, hi)), 3)),
            "data_used_gb":  float(round(float(rng.uniform(0.1, 50.0)), 3)),
            "voice_min":     int(rng.integers(0, 600)),
            "sms_count":     int(rng.integers(0, 200)),
            "churn_risk":    float(round(float(rng.uniform(0, 1)), 4)),
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

def run_once() -> None:
    run_id       = f"run-{uuid.uuid4().hex[:12]}"
    now          = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=15)
    window_end   = now
    region       = "demo"
    raw_bucket   = "raw"

    print(f"\n[pipeline] run_id={run_id}")

    # 1. MinIO buckets
    print("[1/12] Ensuring MinIO buckets ...")
    s3 = get_s3()
    ensure_buckets(s3, ["raw", "processed", "curated"])

    # 2–3. Synthetic data
    print("[2/12] Generating synthetic OSS data ...")
    oss_records = generate_oss(200, region)
    print(f"  {len(oss_records)} OSS records generated")

    print("[3/12] Generating synthetic BSS data ...")
    bss_records = generate_bss(200, region)
    print(f"  {len(bss_records)} BSS records generated")

    # 4. Upload to MinIO
    date_prefix = now.strftime("%Y/%m/%d")
    oss_key     = f"oss/{date_prefix}/{run_id}.json"
    bss_key     = f"bss/{date_prefix}/{run_id}.json"

    print("[4/12] Uploading OSS dataset to MinIO raw layer ...")
    upload_json(s3, raw_bucket, oss_key, oss_records)

    print("[5/12] Uploading BSS dataset to MinIO raw layer ...")
    upload_json(s3, raw_bucket, bss_key, bss_records)

    with get_conn() as conn:
        with conn.cursor() as cur:

            # 5. pipeline_runs
            print("[6/12] Inserting pipeline_runs record ...")
            cur.execute(
                "INSERT INTO pipeline_runs (run_id, status) VALUES (%s, %s);",
                (run_id, "started"),
            )

            # 6. dataset_registry
            print("[7/12] Inserting dataset_registry records ...")
            cur.execute(
                """INSERT INTO dataset_registry
                     (run_id, dataset_type, layer, format, object_key, row_count)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (run_id, "oss", "raw", "json", oss_key, len(oss_records)),
            )
            cur.execute(
                """INSERT INTO dataset_registry
                     (run_id, dataset_type, layer, format, object_key, row_count)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (run_id, "bss", "raw", "json", bss_key, len(bss_records)),
            )

            # 7. Feature engineering
            print("[8/12] Computing KPI features from OSS data ...")
            features = compute_oss_features(oss_records)
            print(f"  mean_latency={features['mean_latency_ms']}ms  "
                  f"mean_loss={features['mean_packet_loss_pct']}%  "
                  f"mean_tput={features['mean_throughput_mbps']}Mbps")

            # 8. SLA risk inference
            print("[9/12] Calling AI service /infer/sla-risk ...")
            score, explanation, model_version = infer_sla_risk(
                run_id, region, window_start, window_end, features
            )
            print(f"  risk_score={score}  model={model_version}")

            # 9. Anomaly detection
            print("[10/12] Calling AI service /infer/anomaly ...")
            anomaly_result = infer_anomaly(run_id, region, oss_records)
            anomaly_rate   = anomaly_result["anomaly_rate"]
            anomaly_count  = anomaly_result["anomalous_count"]
            print(f"  anomalous={anomaly_count}/{len(oss_records)}  rate={anomaly_rate}")

            # 10. sla_risk_scores
            print("[11/12] Persisting SLA risk score ...")
            cur.execute(
                """INSERT INTO sla_risk_scores
                     (run_id, region, window_start, window_end, score, explanation, model_version)
                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (
                    run_id, region, window_start, window_end,
                    score,
                    psycopg2.extras.Json(explanation),
                    model_version,
                ),
            )

            # 11. anomalies — store detected anomalous records individually
            anomaly_records   = [r for r in anomaly_result["records"] if r["is_anomaly"]]
            anomaly_mv        = anomaly_result.get("model_version", model_version)
            for anom in anomaly_records:
                idx = anom["index"]
                src = oss_records[idx]
                cur.execute(
                    """INSERT INTO anomalies
                         (run_id, ts, region, cell_id, kpi_name, severity,
                          value, baseline_value, model_version)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (
                        run_id,
                        src["ts"],
                        src["region"],
                        src["cell_id"],
                        "composite_kpi",
                        round(anom["anomaly_score"], 4),
                        src["latency_ms"],       # representative KPI value
                        25.0,                   # baseline latency
                        anomaly_mv,
                    ),
                )

            # 12. finish
            cur.execute(
                "UPDATE pipeline_runs SET status=%s, finished_at=now() WHERE run_id=%s;",
                ("succeeded", run_id),
            )

    print(f"[12/12] Pipeline run {run_id} succeeded — "
          f"sla_risk={score}  anomalies={anomaly_count}")



def main() -> None:
    print("pipeline-worker: starting vertical slice execution")
    run_once()
    print("pipeline-worker: execution complete")


if __name__ == "__main__":
    main()
