"""
Pipeline Worker — Vertical Slice
Sequence:
  1. Ensure MinIO buckets exist (raw / processed / curated layers)
  2. Generate synthetic OSS dataset (network KPIs)
  3. Generate synthetic BSS dataset (revenue / usage)
  4. Upload both datasets to MinIO raw layer
  5. Insert dataset_registry records
  6. Insert pipeline_runs record
  7. Call AI service /infer/sla-risk
  8. Insert sla_risk_scores record
  9. Mark pipeline_run as succeeded
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
    """Synthetic BSS records — revenue and data consumption per subscriber."""
    rng   = np.random.default_rng(seed)
    plans = ["basic", "standard", "premium"]
    now   = datetime.now(timezone.utc)
    rows  = []
    for i in range(n):
        ts = now - timedelta(minutes=n - i)
        rows.append({
            "ts":            ts.isoformat(),
            "region":        region,
            "subscriber_id": f"SUB-{rng.integers(10000, 99999)}",
            "plan":          plans[i % len(plans)],
            "revenue_usd":   float(round(float(rng.uniform(5, 120)), 2)),
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


# ── AI inference ──────────────────────────────────────────────────────────────

def infer_sla_risk(run_id: str, region: str,
                   window_start: datetime, window_end: datetime) -> tuple[float, dict, str]:
    base = os.getenv("AI_SERVICE_URL", "http://ai-service:8001").rstrip("/")
    payload = {
        "run_id":       run_id,
        "region":       region,
        "window_start": window_start.isoformat(),
        "window_end":   window_end.isoformat(),
    }
    r = requests.post(f"{base}/infer/sla-risk", json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    return float(data["score"]), data.get("explanation", {}), data.get("model_version", "v0.1")


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
    print("[1/9] Ensuring MinIO buckets ...")
    s3 = get_s3()
    ensure_buckets(s3, ["raw", "processed", "curated"])

    # 2. Synthetic data
    print("[2/9] Generating synthetic OSS data ...")
    oss_records = generate_oss(200, region)
    print(f"  {len(oss_records)} OSS records generated")

    print("[3/9] Generating synthetic BSS data ...")
    bss_records = generate_bss(200, region)
    print(f"  {len(bss_records)} BSS records generated")

    # 4. Upload to MinIO
    date_prefix = now.strftime("%Y/%m/%d")
    oss_key     = f"oss/{date_prefix}/{run_id}.json"
    bss_key     = f"bss/{date_prefix}/{run_id}.json"

    print("[4/9] Uploading OSS dataset to MinIO raw layer ...")
    upload_json(s3, raw_bucket, oss_key, oss_records)

    print("[5/9] Uploading BSS dataset to MinIO raw layer ...")
    upload_json(s3, raw_bucket, bss_key, bss_records)

    with get_conn() as conn:
        with conn.cursor() as cur:

            # 5. pipeline_runs
            print("[6/9] Inserting pipeline_runs record ...")
            cur.execute(
                "INSERT INTO pipeline_runs (run_id, status) VALUES (%s, %s);",
                (run_id, "started"),
            )

            # 6. dataset_registry
            print("[7/9] Inserting dataset_registry records ...")
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

            # 7. AI inference
            print("[8/9] Calling AI service /infer/sla-risk ...")
            score, explanation, model_version = infer_sla_risk(
                run_id, region, window_start, window_end
            )
            print(f"  score={score}  model_version={model_version}")

            # 8. sla_risk_scores
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

            # 9. finish pipeline_run
            cur.execute(
                "UPDATE pipeline_runs SET status=%s, finished_at=now() WHERE run_id=%s;",
                ("succeeded", run_id),
            )

    print(f"[9/9] Pipeline run {run_id} succeeded — score={score}")


def main() -> None:
    print("pipeline-worker: starting vertical slice execution")
    run_once()
    print("pipeline-worker: execution complete")


if __name__ == "__main__":
    main()
