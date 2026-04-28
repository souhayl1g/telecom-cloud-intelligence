"""22-step pipeline orchestration."""
import hashlib
import uuid
from datetime import datetime, timezone, timedelta

import numpy as np
import psycopg2.extras

from worker.config import SYNTHETIC_N_RECORDS
from worker.db import get_conn
from worker.storage import get_s3, ensure_buckets, upload_json
from worker.generators.oss import generate_oss
from worker.generators.bss import generate_bss
from worker.processors.oss import build_processed_oss
from worker.processors.bss import build_processed_bss, build_curated_dataset
from worker.analytics.features import compute_oss_features, compute_bss_features
from worker.analytics.correlations import compute_correlations
from worker.inference.client import infer_sla_risk, infer_anomaly, infer_revenue_anomaly
from worker.sampler import USE_REAL_DATA, sample_bss_records, sample_oss_records


def _enrich_bss_for_inference(bss_sampled: list[dict], seed: int) -> list[dict]:
    """Merge sampled subscriber identity with synthetic revenue/churn fields.

    Real BSS data does not contain revenue_tnd or churn_risk (CEM data, not billing).
    We generate plausible synthetic values correlated with the subscriber's
    network quality profile so the downstream v2.0 revenue-anomaly model still
    receives a compatible schema. This is a bridge until real billing data arrives.
    """
    rng = np.random.default_rng(seed)
    enriched = []
    for rec in bss_sampled:
        # Use network experience as a proxy for "value"
        ne_index = rec.get("s1_mme_sr", 0.5) * 0.5 + rec.get("iu_attach_sr", 0.5) * 0.3 + rec.get("gb_attach_sr", 0.5) * 0.2
        base_revenue = 10.0 + ne_index * 40.0  # 10-50 TND range
        revenue = round(base_revenue * rng.uniform(0.7, 1.3), 2)
        churn_risk = round(max(0.0, min(1.0, 1.0 - ne_index + rng.normal(0, 0.1))), 4)
        enriched.append({
            **rec,
            "revenue_tnd": revenue,
            "data_used_gb": round((rec.get("dou_total", 0) / 1e9) * rng.uniform(0.8, 1.2), 2),
            "voice_min": round(rng.uniform(0, 300), 1),
            "sms_count": int(rng.uniform(0, 100)),
            "churn_risk": churn_risk,
            "operator": "TT",
            "line_type": "prepaid" if rng.random() < 0.8 else "postpaid",
            "plan": "default",
        })
    return enriched


def run_once() -> None:
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=15)
    window_end = now
    region = "demo"

    # Derive reproducible seed from run_id (different data each run)
    run_seed = int(hashlib.sha256(run_id.encode()).hexdigest()[:8], 16) % (2**31)

    print(f"\n[pipeline] run_id={run_id}  seed={run_seed}")

    # Record pipeline start BEFORE any work so started_at captures real total time
    with get_conn() as conn:
        with conn.cursor() as cur:
            print("[1/22] Inserting pipeline_runs record ...")
            cur.execute(
                "INSERT INTO pipeline_runs (run_id, status) VALUES (%s, %s);",
                (run_id, "started"),
            )

    try:
        _run_pipeline_steps(run_id, now, window_start, window_end, region, run_seed)
    except Exception as e:
        print(f"\n[pipeline] ✗ run {run_id} FAILED: {e}")
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE pipeline_runs SET status=%s, finished_at=now(), error_message=%s WHERE run_id=%s;",
                        ("failed", str(e)[:500], run_id),
                    )
        except Exception as db_err:
            print(f"[pipeline] could not update pipeline_runs: {db_err}")
        raise


def _run_pipeline_steps(
    run_id: str,
    now: datetime,
    window_start: datetime,
    window_end: datetime,
    region: str,
    run_seed: int,
) -> None:
    # ── 2. MinIO buckets ───────────────────────────────────────────────
    print("[2/22] Ensuring MinIO buckets ...")
    s3 = get_s3()
    ensure_buckets(s3, ["raw", "processed", "curated"])

    # ── 3–4. Data generation (real or synthetic) ─────────────────────────
    if USE_REAL_DATA:
        print("[3/22] Sampling real OSS data from Postgres ...")
        oss_records = sample_oss_records(SYNTHETIC_N_RECORDS)
        fault_info = {
            "fault_cells": [],
            "fault_start_idx": 0,
            "fault_end_idx": 0,
            "fault_records": sum(1 for r in oss_records if r.get("is_fault")),
        }
        print(
            f"  {len(oss_records)} OSS records sampled — "
            f"faults: {fault_info['fault_records']} records"
        )

        print("[4/22] Sampling real BSS subscriber data from Postgres ...")
        bss_sampled = sample_bss_records(SYNTHETIC_N_RECORDS)
        bss_records = _enrich_bss_for_inference(bss_sampled, run_seed)
        print(f"  {len(bss_records)} BSS records sampled + enriched")
    else:
        print("[3/22] Generating synthetic OSS data (with fault injection) ...")
        oss_records, fault_info = generate_oss(SYNTHETIC_N_RECORDS, region, seed=run_seed)
        print(
            f"  {len(oss_records)} OSS records — "
            f"faults: {fault_info['fault_records']} records on cells {fault_info['fault_cells']}"
        )

        print("[4/22] Generating synthetic BSS data (with correlated dips) ...")
        bss_records = generate_bss(SYNTHETIC_N_RECORDS, region, seed=run_seed + 1, fault_info=fault_info)
        print(f"  {len(bss_records)} BSS records generated")

    # ── 5–6. Upload raw layer ────────────────────────────────────────────
    date_prefix = now.strftime("%Y/%m/%d")
    oss_key = f"oss/{date_prefix}/{run_id}.json"
    bss_key = f"bss/{date_prefix}/{run_id}.json"

    print("[5/22] Uploading OSS dataset to MinIO raw layer ...")
    upload_json(s3, "raw", oss_key, oss_records)

    print("[6/22] Uploading BSS dataset to MinIO raw layer ...")
    upload_json(s3, "raw", bss_key, bss_records)

    with get_conn() as conn:
        with conn.cursor() as cur:

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
            print(
                f"  OSS: mean_lat={features['mean_latency_ms']}ms  "
                f"mean_loss={features['mean_packet_loss_pct']}%  "
                f"mean_tput={features['mean_throughput_mbps']}Mbps"
            )
            print(
                f"  BSS: mean_rev={bss_features['mean_revenue_tnd']}TND  "
                f"mean_churn={bss_features['mean_churn_risk']}"
            )

            # ── 12. SLA risk inference ───────────────────────────────────
            print("[12/22] Calling AI service /infer/sla-risk ...")
            score, explanation, model_version = infer_sla_risk(
                run_id, region, window_start, window_end, features
            )
            print(f"  risk_score={score}  model={model_version}")

            # ── 13. OSS anomaly detection ────────────────────────────────
            print("[13/22] Calling AI service /infer/anomaly ...")
            anomaly_result = infer_anomaly(run_id, region, oss_records)
            print(
                f"  OSS anomalies: {anomaly_result['anomalous_count']}/{len(oss_records)}  "
                f"rate={anomaly_result['anomaly_rate']}"
            )

            # ── 14. Revenue anomaly detection ────────────────────────────
            print("[14/22] Calling AI service /infer/revenue-anomaly ...")
            rev_anomaly_result = infer_revenue_anomaly(run_id, region, bss_records)
            print(
                f"  BSS anomalies: {rev_anomaly_result['anomalous_count']}/{len(bss_records)}  "
                f"rate={rev_anomaly_result['anomaly_rate']}"
            )

            # ── 15. OSS↔BSS correlations ───────────────────────────────
            print("[15/22] Computing OSS↔BSS correlations ...")
            correlations = compute_correlations(oss_records, bss_records)
            for c in correlations:
                print(
                    f"  {c['method']:>8s}  {c['metric_x']:<28s} ↔ {c['metric_y']:<22s}  "
                    f"r={c['corr_value']:+.4f}  p={c['p_value']:.4f}"
                )

            # ── 16. Curated dataset ──────────────────────────────────────
            print("[16/22] Building curated dataset → curated layer ...")
            curated = build_curated_dataset(
                oss_records,
                bss_records,
                anomaly_result,
                rev_anomaly_result,
                score,
                correlations,
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
                (
                    run_id,
                    region,
                    window_start,
                    window_end,
                    score,
                    psycopg2.extras.Json(explanation),
                    model_version,
                ),
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
                    (
                        run_id,
                        src["ts"],
                        src["region"],
                        src["cell_id"],
                        "composite_kpi",
                        round(anom["anomaly_score"], 4),
                        src["latency_ms"],
                        25.0,
                        anomaly_result.get("model_version", "v2.0"),
                    ),
                )

            # ── 20. Persist revenue anomalies ────────────────────────────
            print("[20/22] Persisting revenue anomalies ...")
            bss_anom_records = [
                r for r in rev_anomaly_result["records"] if r["is_anomaly"]
            ]
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
                    (
                        run_id,
                        src["ts"],
                        src["region"],
                        src["operator"],
                        src["subscriber_id"],
                        src["line_type"],
                        src["plan"],
                        "composite_bss",
                        round(anom["anomaly_score"], 4),
                        src["revenue_tnd"],
                        bss_features["mean_revenue_tnd"],
                        rev_anomaly_result.get("model_version", "v2.0"),
                    ),
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
                    (
                        run_id,
                        region,
                        c["metric_x"],
                        c["metric_y"],
                        window_start,
                        window_end,
                        c["method"],
                        c["corr_value"],
                        c["p_value"],
                    ),
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
    print(
        f"  BSS anomalies:   {rev_anomaly_result['anomalous_count']}/{len(bss_records)}"
    )
    print(f"  Correlations:    {len(correlations)} computed")
    print(
        f"  Fault injection: {fault_info['fault_records']} records on {fault_info['fault_cells']}"
    )
